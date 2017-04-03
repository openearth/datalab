import copy
import base64
import urlparse
from django.conf import settings
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, login, logout, authenticate
)
from django import http
from django.views.generic import View, FormView, TemplateView
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.core.context_processors import csrf
from django.contrib.auth.models import User
import redis
from ws4redis import settings as redis_settings
from openearth.apps.script_execution_manager.store import RedisHistoryStore
from openearth.forms import PasswordPolicyAuthenticationForm


def logout_view(request):
    logout(request)
    return http.HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)


class BaseTemplateView(TemplateView):

    def __init__(self):
        self._connection = redis.StrictRedis(**redis_settings.WS4REDIS_CONNECTION)
        self.redis_store = RedisHistoryStore(self._connection)

    def get_context_data(self, **kwargs):
        context = super(BaseTemplateView, self).get_context_data(**kwargs)

        self.request.META['SERVER_NAME'] = getattr(settings, 'SERVER_NAME')
        self.request.META['WEBSOCKET_URL'] = getattr(settings, 'WEBSOCKET_URL')
        self.request.META['SCHEMA'] = 'ws'
        if self.request.META['wsgi.url_scheme'] == 'https':
            self.request.META['SCHEMA'] = 'wss'

        context.update(ws_url='{SCHEMA}://{SERVER_NAME}:{SERVER_PORT}{WEBSOCKET_URL}foobar'.format(**self.request.META))
        return context


class WebsocketView(BaseTemplateView):

    template_name = 'websocket.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context.update(csrf(request))
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        users = User.objects.all()
        context = super(WebsocketView, self).get_context_data(**kwargs)
        context.update(users=users)
        return context

    def post(self, request, *args, **kwargs):
        channels = ['subscribe-user', 'publish-user']
        new_req = copy.copy(request)
        new_req.path_info = '/ws/foobar'
        self.redis_store.subscribe_channels(new_req, channels)
        self.redis_store.publish_message(request.POST.get('message'))
        return http.HttpResponse('OK')


class AuthView(View):
    def get(self, request):
        # Disable csrf processing completely
        request.csrf_processing_done = True

        response = http.HttpResponse()
        authorization = request.META.get('HTTP_AUTHORIZATION')
        if authorization:
            encoded = authorization.split(' ', 1)[1]
            username, password = base64.decodestring(encoded).split(':', 1)
            user = authenticate(username=username, password=password)

            if user is not None:
                response = http.HttpResponse()
                login(self.request, user)

                self.request.session['authorization'] = 'Basic %s' % (
                    base64.b64encode(b'%s:%s' % (username, password)))

        elif request.user.is_authenticated():
            authorization = request.session.get('authorization')

        response['Authorization'] = authorization or ''
        return response


class LoginView(FormView):
    form_class = AuthenticationForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'login.html'
    success_url = '/'

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']

        user = authenticate(username=username,
                            password=password)
        if user is not None:
            if user.is_active:
                login(self.request, user)
                # set is_staff status to ldap member of admins state
                member_of_admins = getattr(user, 'member_of_admins', None)
                if member_of_admins is not None and member_of_admins != user.is_staff:
                    user.is_staff = member_of_admins
                    user.save()

                self.request.session['authorization'] = 'Basic %s' % (
                    base64.b64encode(b'%s:%s' % (username, password)))

                return super(LoginView, self).form_valid(form)

        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        return super(LoginView, self).form_invalid(form)

    def get_success_url(self):
        if self.success_url:
            redirect_to = self.success_url
        else:
            redirect_to = self.request.REQUEST.get(self.redirect_field_name, '')

        netloc = urlparse.urlparse(redirect_to)[1]
        if not redirect_to:
            redirect_to = settings.LOGIN_REDIRECT_URL
        elif netloc and netloc != self.request.get_host():
            redirect_to = settings.LOGIN_REDIRECT_URL
        return redirect_to

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
