from models import ProcessingEnvironment, ProcessingJob
from widgets import BootstrapDatetimePickerWidget, TerminalWidget
from django import forms
from django.conf import settings
from openearth.apps.processing.fields import InterpreterField
from openearth.libs import svn


class ProcessingJobImageAdminForm(forms.ModelForm):
    interpreter = InterpreterField(required_keys=['script_path'])


class EnvironmentForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(EnvironmentForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            for field in ('repo', 'name'):
                self.fields[field].widget.attrs['class'] = 'form-control'

    def clean_repo(self):

        script_exts = ('.py', '.m')
        repo = self.cleaned_data['repo']
        if repo.startswith('/'):
            repo = repo[1:]
        if not repo.endswith('/'):
            repo = "%s/" % repo

        url = '{0}{1}{2}'.format(ProcessingEnvironment.REPOS.SVN['url'], repo, ProcessingEnvironment.REPOS.SVN['scripts'])

        try:
            output, err = svn.list_(url, ProcessingEnvironment.REPOS.SVN['username'], ProcessingEnvironment.REPOS.SVN['password'])
        except Exception, err:
            raise forms.ValidationError(err)

        if not [i for i in range(len(output)) if output[i].endswith(script_exts)]:
            raise forms.ValidationError(
                "No files with the extensions {0} found in {1}".format(', '.join(script_exts), url)
            )
        return repo

    class Meta:
        model = ProcessingEnvironment
        fields = ['name', 'repo', 'libvirt_image', 'open_earth']


class JobAdminForm(forms.ModelForm):
    terminal = forms.CharField(widget=TerminalWidget,)

    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop('request', None)

        super(JobAdminForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            for field in ('terminal',):
                self.request.META['SERVER_NAME'] = getattr(settings, 'SERVER_NAME')
                self.request.META['WEBSOCKET_URL'] = getattr(settings, 'WEBSOCKET_URL')
                self.request.META['SCHEMA'] = 'ws'
                self.request.META['UUID'] = instance.uuid
                if self.request.META['wsgi.url_scheme'] == 'https':
                    self.request.META['SCHEMA'] = 'wss'

                self.fields[field].required = False
                self.fields[field].widget.attrs['data-ws-url'] = '{SCHEMA}://{SERVER_NAME}:{SERVER_PORT}{WEBSOCKET_URL}{UUID}'.format(**self.request.META)
                self.fields[field].widget.attrs['data-ws-type'] = 'subscribe-superuser'
                self.fields[field].widget.attrs['id'] = 'terminal'

    class Meta:
        model = ProcessingJob


class JobForm(forms.ModelForm):
    start = forms.DateTimeField(label="Planned start",
                                widget=BootstrapDatetimePickerWidget,
                                localize=True)
    status = forms.ChoiceField(widget=forms.Select(),
                               initial=ProcessingJob.STATUS.CREATED,
                               choices=ProcessingJob.STATUS.choices)
    open_earth_revision = forms.IntegerField(min_value=1, widget=forms.Select,
                                             required=False)

    def __init__(self, *args, **kwargs):
        super(JobForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        data = kwargs.get('data', {})

        # Custom group attribute to split within the template
        self.fields['revision'].widget.group = 'advanced'
        self.fields['script_revision'].widget.group = 'advanced'
        self.fields['open_earth_revision'].widget.group = 'advanced'

        if instance:
            def get_field(f):
                return instance._meta.get_field_by_name(f)[0]

            self.fields['revision'].choices = get_field('revision').choices
            self.fields['script'].choices = get_field('script').choices
            self.fields['script_revision'].choices = (
                (self.fields['script_revision'].choices[0],)
                + instance.environment.get_script_revisions(
                    data.get('script', '')))

            if not instance.environment.open_earth:
                self.fields['open_earth_revision'].widget.attrs['disabled'] \
                    = 'disabled'

            for field in ('status', 'environment'):
                self.fields[field].required = False
                self.fields[field].widget.attrs['disabled'] = 'disabled'

    def clean_revision(self):
        revision = self.cleaned_data['revision'] or 'HEAD'
        new_revision = self.instance.environment.get_repo_revisions(
            revision=revision)

        if new_revision:
            self.fields['revision'].choices = new_revision
            return int(new_revision[0][0])
        else:
            raise forms.ValidationError('Revision %r is not a valid revision' %
                                        revision)

    def clean_status(self):
        instance = getattr(self, 'instance', None)
        return instance.status

    def clean_environment(self):
        instance = getattr(self, 'instance', None)
        return instance.environment

    class Meta:
        model = ProcessingJob
        fields = ['status', 'environment', 'start', 'auto_commit', 'script',
                  'revision', 'script_revision', 'open_earth_revision', ]
