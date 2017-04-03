from openearth.libs.svn import SvnRepoDoesNotExist

__author__ = 'Jelle'
from django.conf import settings
from django.http import Http404
from django.views.generic import ListView, CreateView, UpdateView, View
from django.views.generic.detail import DetailView
import models
from forms import EnvironmentForm, JobForm
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _, ugettext
from django.shortcuts import get_object_or_404, redirect
import json
from django.http import HttpResponse
import redis
from ws4redis import settings as redis_settings


class JsonResponse(HttpResponse):
    def __init__(self, content={}, mimetype=None, status=None,
                 content_type='application/json'):
        super(JsonResponse, self).__init__(json.dumps(content), mimetype=mimetype,
                                           status=status, content_type=content_type)


class EnvironmentListView(ListView):
    model = models.ProcessingEnvironment
    template_name = 'environment_list.html'

    def get_queryset(self, request):
        self.queryset = self.model.objects.author(request.user).all()
        return super(ListView, self).get_queryset()

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset(request)
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if (self.get_paginate_by(self.object_list) is not None
                and hasattr(self.object_list, 'exists')):
                is_empty = not self.object_list.exists()
            else:
                is_empty = len(self.object_list) == 0
            if is_empty:
                raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.")
                        % {'class_name': self.__class__.__name__})
        context = self.get_context_data()
        return self.render_to_response(context)


class EnvironmentCreateView(CreateView):
    form_class = EnvironmentForm
    model = models.ProcessingEnvironment
    template_name = 'environment_create.html'
    fields = ['repo', 'name', 'open_earth', 'libvirt_image']

    def form_valid(self, form):
        messages.success(self.request, _("Environment successfully created"), extra_tags='alert alert-success alert-dismissable')
        form.instance.author = self.request.user
        return super(EnvironmentCreateView, self).form_valid(form)


class EnvironmentUpdateView(UpdateView):
    form_class = EnvironmentForm
    model = models.ProcessingEnvironment
    template_name = 'environment_update.html'
    fields = ['repo', 'name', 'open_earth']

    def get(self, request, *args, **kwargs):
        result = super(EnvironmentUpdateView, self).get(request, *args, **kwargs)
        if self.object.jobs:
            return redirect('environment_detail', pk=self.object)
        else:
            return result

    def form_valid(self, form):
        messages.success(self.request, _("Change successfully saved"), extra_tags='alert alert-success alert-dismissable')
        form.instance.author = self.request.user
        return super(EnvironmentUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        # get all jobs related to the ProcessingEnvironment
        context['job_list'] = models.ProcessingJob.objects.filter(environment=self.object)
        return context

class EnvironmentDetailView(ListView):
    model = models.ProcessingJob
    template_name = 'environment_detail.html'
    context_object_name = "job_list"
    paginate_by = 10

    def get_queryset(self):
        return models.ProcessingJob.objects.filter(environment__id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(EnvironmentDetailView, self).get_context_data(**kwargs)
        # get all jobs related to the ProcessingEnvironment
        context['object'] = models.ProcessingEnvironment.objects.get(id=self.kwargs['pk'])
        return context

# class EnvironmentDetailView(DetailView):
#     model = models.ProcessingEnvironment
#     template_name = 'environment_detail.html'
#     context_object_name = "object"
#     paginate_by = 2
#
#     def get_context_data(self, **kwargs):
#         context = super(DetailView, self).get_context_data(**kwargs)
#         # get all jobs related to the ProcessingEnvironment
#         context['job_list'] = models.ProcessingJob.objects.filter(environment=self.object)
#         return context


class JobListView(ListView):
    model = models.ProcessingJob
    template_name = 'job_list.html'


    def get_queryset(self):
        self.queryset = self.model.objects.filter(environment=self.kwargs['env']).all()
        return super(JobListView, self).get_queryset()

    def get_context_data(self, **kwargs):
        context = super(JobListView, self).get_context_data(**kwargs)
        context.update({
            'environment': models.ProcessingEnvironment.objects.get(id=self.kwargs['env']),
        })
        return context


class JobCreateView(CreateView):
    form_class = JobForm
    model = models.ProcessingJob
    template_name = 'job_create.html'
    fields = ['start', 'status', 'auto_commit', 'revision', 'script_revision']

    def get(self, request, *args, **kwargs):
        env = get_object_or_404(models.ProcessingEnvironment, pk=self.kwargs['env'])
        self.object = models.ProcessingJob(environment=env)

        form_class = self.get_form_class()

        # if we can not set the environment --> the SVN repo is invalid
        try:
            form = form_class(instance=self.object, initial={
                "environment": env,
            })
        except SvnRepoDoesNotExist:
            form = None

        context = self.get_context_data(form=form, env=env)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        env = get_object_or_404(models.ProcessingEnvironment, pk=self.kwargs['env'])
        self.object = models.ProcessingJob(environment=env)

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.status = models.ProcessingJob.STATUS.CREATED
        result = super(JobCreateView, self).form_valid(form)
        return result


class RepoRevisionsView(View):
    def get(self, request, *args, **kwargs):
        env = get_object_or_404(models.ProcessingEnvironment, pk=self.kwargs['env'])
        return JsonResponse(env.get_revisions())


class ScriptsView(View):
    def get(self, request, *args, **kwargs):
        env = get_object_or_404(models.ProcessingEnvironment, pk=self.kwargs['env'])
        return JsonResponse(env.get_script_choices())


class OpenEarthRevisionsView(View):
    def get(self, request, *args, **kwargs):
        extension = self.kwargs.get('extension')
        revision = request.GET.get('revision', '')
        if revision:
            revision = '%d:0' % (int(revision) - 1)

        if extension == 'py' or extension.endswith('.py'):
            revisions = models.get_open_earth_python_revisions(revision=revision)
        elif extension == 'm' or extension.endswith('.m'):
            revisions = models.get_open_earth_matlab_revisions(revision=revision)
        else:
            revisions = models.get_open_earth_revisions(revision=revision)

        for revision in revisions:
            revision['id'] = revision['@revision']

        return JsonResponse(revisions)


class ScriptRevisionsView(View):
    def get(self, request, *args, **kwargs):
        env = get_object_or_404(models.ProcessingEnvironment, pk=self.kwargs['env'])
        return JsonResponse(env.get_script_revisions(self.kwargs['script']))


class JobUpdateView(UpdateView):
    form_class = JobForm
    model = models.ProcessingJob
    slug_url_kwarg = 'uuid'
    slug_field = 'uuid'
    template_name = 'job_update.html'
    fields = ['start', 'status', 'auto_commit', 'environment']

    def form_valid(self, form):
        messages.success(self.request, _("Job successfully saved"), extra_tags='alert alert-success alert-dismissable')
        return super(JobUpdateView, self).form_valid(form)


class JobDetailView(DetailView):
    model = models.ProcessingJob
    slug_url_kwarg = 'uuid'
    slug_field = 'uuid'
    template_name = 'job_detail.html'

    def __init__(self):
        self._connection = redis.StrictRedis(**redis_settings.WS4REDIS_CONNECTION)
        super(JobDetailView, self).__init__()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.is_ajax():
            response_data = dict()
            job = get_object_or_404(models.ProcessingJob, uuid=self.kwargs['uuid'])
            channel = u'{0}:{1}'.format(request.user.username, job.uuid)

            action = request.GET.get('action', None)
            if action is not None:
                if action == 'stop_job':
                    self._connection.publish(channel, '[WARINING] Trying to stop Job')
                    job.stop_job()
                    response_data['action'] = None
                    response_data['action_text'] = ugettext('stop job')
                    response_data['status'] = job.get_status_display()

                elif action == 'check_status':
                    response_data['status'] = job.get_current_status()
                    response_data['status_value'] = job.status

            return JsonResponse(response_data)

        return super(JobDetailView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(JobDetailView, self).get_context_data(**kwargs)
        self.request.META['SERVER_NAME'] = getattr(settings, 'SERVER_NAME')
        self.request.META['WEBSOCKET_URL'] = getattr(settings, 'WEBSOCKET_URL')
        self.request.META['SCHEMA'] = 'ws'
        self.request.META['UUID'] = self.kwargs['uuid']
        if self.request.META['wsgi.url_scheme'] == 'https':
            self.request.META['SCHEMA'] = 'wss'

        context.update({
            'ws_url': '{SCHEMA}://{SERVER_NAME}:{SERVER_PORT}{WEBSOCKET_URL}{UUID}'.format(**self.request.META),
            'environment': get_object_or_404(models.ProcessingEnvironment, pk=self.kwargs['env']),
            'job': get_object_or_404(models.ProcessingJob, uuid=self.kwargs['uuid']),
        })
        return context
