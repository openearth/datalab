from __future__ import unicode_literals
import urlparse
from celery.result import AsyncResult
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.db import models
from django.conf import settings
from django.utils import timezone
from django_extensions.db.fields import PostgreSQLUUIDField
from filer.fields.file import FilerFileField
from openearth.apps.script_execution_manager.tasks import commit
from django.utils.functional import lazy
from openearth.libs import svn
from django.core import exceptions
import reversion


def get_revisions(url, username, password, limit=100, revision=None,
                  format=False):
    revisions = svn.revisions(
        url=url,
        username=username,
        password=password,
        limit=limit,
        revision=revision)

    if format:
        formatted = []
        for revision in revisions:
            formatted.append((
                int(revision['@revision']),
                '[%(@revision)s] %(msg)s @ %(date)s by %(author)s' % revision,
            ))

        return tuple(formatted)
    else:
        return revisions


def get_open_earth_python_revisions(limit=100, revision=None, format=False):
    return get_revisions(
        url=settings.OPEN_EARTH_TOOLS_PYTHON_URL,
        username=settings.OPEN_EARTH_TOOLS_PYTHON_USERNAME,
        password=settings.OPEN_EARTH_TOOLS_PYTHON_PASSWORD,
        limit=limit,
        revision=revision,
        format=format,
    )


def get_open_earth_matlab_revisions(limit=100, revision=None, format=False):
    return get_revisions(
        url=settings.OPEN_EARTH_TOOLS_MATLAB_URL,
        username=settings.OPEN_EARTH_TOOLS_MATLAB_USERNAME,
        password=settings.OPEN_EARTH_TOOLS_MATLAB_PASSWORD,
        limit=limit,
        revision=revision,
        format=format,
    )


def get_open_earth_revisions(limit=100, revision=None, format=False):
    return get_revisions(
        url=settings.OPEN_EARTH_TOOLS_URL,
        username=settings.OPEN_EARTH_TOOLS_USERNAME,
        password=settings.OPEN_EARTH_TOOLS_PASSWORD,
        limit=limit,
        revision=revision,
        format=format,
    )


class Extension(models.Model):
    name = models.CharField(max_length=255)
    extension = models.CharField(max_length=32, unique=True)

    def get_name(self):
        return self.name or self.extension

    def __repr__(self):
        return '<%s[%s]%s>' % (
            self.__class__.__name__,
            self.extension,
            self.name or '',
        )

    def __unicode__(self):
        return unicode(self.get_name())


@reversion.register
class ProcessingJobImage(models.Model):
    interpreter = models.CharField(
        _('interpreter'), max_length=255,
        help_text=_('e.g /opt/python2.7/bin/python'))
    libvirt_image = models.FilePathField(
        _('image'), path=settings.CONTAINER['base_dir'])
    name = models.CharField(
        _('name'), max_length=255, help_text=_('e.g python 2.7'))
    description = models.TextField(_('description'), help_text=_(
        'describe which libraries are available in this environment'))
    extensions = models.ManyToManyField(Extension, blank=True)

    def __unicode__(self):
        try:
            return u'%s' % self.name
        except AttributeError:
            return '%s[%d]' % (self.__class__.__name__, self.id)

    class Meta:
        verbose_name = _('libvirt image')
        verbose_name_plural = _('libvirt images')


class ProcessingEnvironmentManager(models.Manager):
    def author(self, author):
        return super(ProcessingEnvironmentManager,
                     self).get_queryset().filter(author=author)


@reversion.register
class ProcessingEnvironment(models.Model):
    class REPOS:
        SVN = getattr(settings, "ENVIRONMENT_SVN_SETTINGS", None)

    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    libvirt_image = models.ForeignKey(
        ProcessingJobImage, verbose_name=_('processing environment'),
        help_text=_('The environment required for your processing script.'))
    repo = models.CharField(_('relative SVN repo url'), max_length=255, help_text=_('The relative position of the svn repo folder containing your [raw/] and [scripts/] directories. The root of the svn repository is: {0}').format(REPOS.SVN['url']))
    name = models.CharField(_('name'), max_length=50, blank=False, null=False, help_text=_('A custom name for your environment.'))
    open_earth = models.BooleanField(_('use OpenEarth tools'), default=False, help_text=_('Enable this if your script needs OpenEarth tools for processing the raw data.'))
    created_date = models.DateTimeField(_('date created'), default=timezone.now)

    objects = ProcessingEnvironmentManager()

    @property
    def jobs(self):
        return self.processing_environment.all().filter(environment=self.id)

    def __unicode__(self):

        try:
            return u'%s' % self.name
        except AttributeError:
            return '%s[%d]' % (self.__class__.__name__, self.id)

    def get_absolute_url(self):
        return reverse('environment_detail', kwargs={'pk': self.pk})

    def get_repo_url(self):
        return '{0}{1}'.format(self.REPOS.SVN['url'], self.repo)

    def invalid_repo(self):
        try:
            self.get_repo_revisions()
        except svn.SvnRepoDoesNotExist, e:
            return e

    def get_revisions(self, url, limit=100, revision=None, format=False):
        return get_revisions(
            url=url,
            username=self.REPOS.SVN['username'],
            password=self.REPOS.SVN['password'],
            limit=limit,
            revision=revision,
            format=format,
        )

    def get_repo_revisions(self, limit=100, revision=None, format=True):
        return self.get_revisions(self.get_repo_url(), limit, revision, format)

    def get_scripts_url(self):
        return self.get_repo_url() + self.REPOS.SVN['scripts']

    def get_script_revisions(self, script, limit=10, revision=None,
                             format=True):
        return self.get_revisions(self.get_scripts_url(), limit,
                                  revision, format)

    def get_script_choices(self, for_choices=False):
        output, err = svn.list_(
            url=self.get_scripts_url(),
            username=self.REPOS.SVN['username'],
            password=self.REPOS.SVN['password'])

        # Get the supported extensions for this image
        extensions = tuple(self.libvirt_image.extensions.values_list(
            'extension', flat=True)) or ('.py', '.m')

        scripts = tuple(s for s in output if s.endswith(extensions))

        if for_choices:
            scripts = tuple((s, s) for s in scripts)
        return scripts

    class Meta:
        verbose_name = _('processing environment')
        verbose_name_plural = _('processing environments')
        ordering = ['-created_date']


@reversion.register
class ProcessingJob(models.Model):
    class STATUS(object):
        CREATED = 10
        SCHEDULED = 20
        PENDING = 30
        STARTED = 40
        RUNNING = 50
        FINISHED = 100
        REVOKED = 500
        FAILURE = 999

        choices = [
            (CREATED, _('Created')),
            (SCHEDULED, _('Scheduled')),
            (PENDING, _('Pending')),
            (STARTED, _('Started')),
            (RUNNING, _('Running')),
            (FINISHED, _('Finished successfully')),
            (REVOKED, _('Revoked')),
            (FAILURE, _('Failed')),
        ]

    uuid = PostgreSQLUUIDField(primary_key=True)
    environment = models.ForeignKey(ProcessingEnvironment,
                                    verbose_name=_('processing environment'),
                                    related_name='processing_environment',
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True,)

    start = models.DateTimeField(_('start job after '), default=timezone.now)
    created_date = models.DateTimeField(_('date created'),
                                        default=timezone.now)
    status = models.PositiveIntegerField(_('status'),
                                         default=STATUS.CREATED,
                                         choices=STATUS.choices,
                                         null=True, blank=True)
    auto_commit = models.BooleanField(_('Commit automatically'), default=True)
    script = models.CharField(_('script name'), max_length=255,
                              choices=[(1, 'error')])
    script_revision = models.PositiveIntegerField(
        help_text='Override the script revision, defaults to "revision"',
        null=True, blank=True, choices=[('', '')])
    revision = models.PositiveIntegerField(
        help_text='Execute the data (and scripts) from this revision',
        null=True, blank=True, choices=[('', 'Latest')])
    open_earth_revision = models.PositiveIntegerField(
        help_text='Execute with specific open earth version',
        null=True, blank=True)

    def get_script_revisions(self, limit=10, revision=None, format=True):
        return self.environment.get_revisions(self.get_script_url(False),
                                              limit, revision, format)

    def get_repo_revisions(self, limit=100, revision=None, format=True):
        return self.environment.get_repo_revisions(limit, revision, format)

    def __init__(self, *args, **kwargs):
        super(ProcessingJob, self).__init__(*args, **kwargs)
        self._meta.get_field_by_name('script')[0]._choices = lazy(
            self.get_script_choices, tuple)()
        self._meta.get_field_by_name('script_revision')[0]._choices = lazy(
            self.get_script_revisions, tuple)()
        self._meta.get_field_by_name('revision')[0]._choices = lazy(
            self.get_repo_revisions, tuple)()

    def get_script_choices(self):
        return self.environment.get_script_choices(for_choices=True)

    @property
    def results(self):
        return self.processing_job.all().filter(job=self.uuid)

    def get_script_url(self, with_revision=True):
        url = urlparse.urljoin(self.environment.get_scripts_url(), self.script)
        if self.script_revision and with_revision:
            url += '?p=%s' % self.script_revision
        return url

    def get_repo_url(self):
        url = urlparse.urljoin(self.environment.get_repo_url(), self.repo)
        if self.revision:
            url += '?p=%s' % self.revision
        return url

    def clean(self):
        if self.revision:
            try:
                self.environment.get_repo_revisions(revision=self.revision)
            except Exception, e:
                raise exceptions.ValidationError('Invalid revision %r: %r' % (
                                                 self.revision, e))
        else:
            revision, = self.environment.get_script_revisions(self.script, 1)
            self.revision = revision[0]

        if self.script_revision:
            try:
                self.environment.get_script_revisions(
                    self.script, revision=self.script_revision)
            except Exception, e:
                raise exceptions.ValidationError('Invalid revision %r: %r' % (
                                                 self.script_revision, e))

    def set_status(self, status):
        if hasattr(self.STATUS, status):
            new_status = getattr(self.STATUS, status)
            if new_status > self.status:
                self.status = new_status
            self.save()
        return self.status

    def get_current_status(self):
        res = AsyncResult(self.uuid)

        if(hasattr(self.STATUS, res.status)
                and self.status != getattr(self.STATUS, res.status)):
            self.set_status(res.status)

        return self.get_status_display()

    def start_job(self):
        """
        Starts the processing job.

        Returns:
            The result string of the task.
        """
        from openearth.apps.script_execution_manager.tasks import run_script

        kwargs = {
            'namespace': self.uuid,
            'username': self.environment.author.username,
            'image': self.environment.libvirt_image.libvirt_image,
            'interpreter': self.environment.libvirt_image.interpreter,
            'script_name': self.script,
            'svn_url': self.environment.get_repo_url(),
            'svn_script_path': self.environment.REPOS.SVN['scripts'],
            'revision': str(self.revision or ''),
            'script_revision': str(self.script_revision or ''),
            'open_earth_tools': self.environment.open_earth,
            'open_earth_revision': self.open_earth_revision,
        }
        # Run commit after run_script has run.
        result = run_script.apply_async(
            kwargs=kwargs,
            task_id=self.uuid,
            eta=self.start,
            link=commit.s(
                username=self.environment.author.username,
                namespace=self.uuid,
                user_name=self.environment.author.get_full_name(),
                user_email=self.environment.author.email
            )
        )
        return result

    def stop_job(self):
        from openearth.celery import app
        app.control.revoke(self.uuid, terminate=True, signal='SIGKILL')

    def get_log(self):
        pass

    def get_absolute_url(self):
        return reverse(
            'job_detail',
            kwargs={'env': self.environment.id, 'uuid': self.uuid})

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(ProcessingJob, self).save(force_insert, force_update, using,
                                        update_fields)
        # directly start/schedule job after successful save
        if self.status <= self.STATUS.CREATED:
            self.start_job()

    def __unicode__(self):
        try:
            return u'%s' % self.uuid
        except AttributeError:
            return '%s[%s]' % (self.__class__.__name__, self.pk)

    class Meta:
        verbose_name = _('job')
        verbose_name_plural = _('jobs')
        ordering = ['-created_date']


def result_file_name(instance, filename):
    return '/'.join([
        'job_results',
        instance.job.environment.author.username,
        instance.job.pk,
        filename,
    ])


@reversion.register
class ProcessingJobResult(models.Model):
    job = models.ForeignKey(ProcessingJob,
                            verbose_name=_('processing job'),
                            related_name='processing_result',
                            on_delete=models.SET_NULL,
                            null=True, blank=True, )
    file = FilerFileField(null=True, blank=True)
    committed = models.BooleanField(_('committed'), default=False)

    def __unicode__(self):
        try:
            return u'%s Job' % self.environment.name
        except AttributeError:
            return '%s[%d]' % (self.__class__.__name__, self.id)

    class Meta:
        verbose_name = _('result')
        verbose_name_plural = _('results')
