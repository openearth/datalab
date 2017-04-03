from __future__ import unicode_literals
from celery.utils.log import get_task_logger
from django.core.management import call_command
import logging
import os
from shutil import copyfile
import subprocess
import sys
import openearth
from openearth.apps.script_execution_manager.exec_wrapper import ExecWrapper


class CommitError(BaseException):
    pass


class CommitBase(object):

    def __init__(self, source, dest, processing_job, published=False, user_email=None, user_name=None):
        """
        Arguments:
            source a file
            dest a destination directory
            processing_job UUID of job. This makes it possible to store the
                job ID along with the processed data. Also used to get parent
                logger.
        """
        self.source = source
        self.dest = dest
        self.published = published
        self.processing_job = processing_job
        self.user_email = user_email

        try:
            #check if the user has a full name
            if len(self.user_email) > 4:
                self.user_name = user_name
            else:
                self.user_name = 'Not available'
        except TypeError:
            self.user_name = 'Not available'


    def get_logger(self):
        return logging.getLogger('openearth.apps.script_execution_manager.tasks.{0}'.format(self.processing_job.pk))

    def mark_published(self):
        raise NotImplementedError()

    def mark_unpublished(self):
        raise NotImplementedError()

    def commit(self):
        if self.published:
            self.mark_published()
        else:
            self.mark_unpublished()


class CommitCSV(CommitBase):
    """
    Commits a CSV file to the database and mark data (un)published

    Description:
        Commits data to the database, but sometimes this data has to be checked
        before it is made public. In that case the state of the Observation
        object has to be set to unpublished (TODO: do this).

    """
    def __init__(self, source, processing_job, published=False):
        """
        Arguments:
            source a file
            dest a destination directory
            processing_job ProcessingJob Object. This makes it possible to store
                the job ID along with the processed data. Also used to get parent
                logger.
        """
        self.source = source
        self.published = published
        self.processing_job = processing_job

    def call_commit_command(self, published=True):
        """
        Calls csv_worker command to validate and insert CSV data into db.
        """
        logger = self.get_logger()
        manage_path = os.path.join(
            os.path.dirname(openearth.__file__),
            '..',
            'manage.py'
        )
        cmd = [
            sys.executable,  # Current python interpreter
            manage_path,
            'csv_worker',
            '--processing-job={0}'.format(self.processing_job),
            '--csv-input={0}'.format(self.source),
        ]
        if published:
            cmd += ['--published']
        logger.info('Executing command: "{0}"'.format(' '.join(cmd)))
        ew = ExecWrapper(
            command=cmd,
        )
        for stdout_stderr in ew.start_process():
            logger.info(stdout_stderr)

        if ew.get_return_code():
            raise CommitError('An error occurred while running commit worker.')

    def mark_published(self):
        """
        Commits CSV by calling call_commit_command and marks with published arg
        """
        self.call_commit_command(published=True)

    def mark_unpublished(self):
        """
        Commits CSV by calling call_commit_command and marks it unpublished.

        TODO:
        - call commit command
        - mark UNpublished
        """
        self.call_commit_command(published=False)

    def commit(self):
        if self.published:
            self.mark_published()
        else:
            self.mark_unpublished()


class CommitNetCDF(CommitBase):
    """
    Committing a NetCDF file: copy to destination and mark final/preliminary.

    Usage:
        To commit published:
        c = CommitNetCDF('src.nc', 'dest.nc', published=True)
        c.commit() # Takes published=True into account
        c.mark_published()

        To commit unpublished:
        c = CommitNetCDF('src.nc', 'dest.nc', published=False)
        c.commit() # Takes published=True into account
        c.mark_unpublished()

    """

    def mark_unpublished(self):
        """
        Mark NetCDF data unpublished and move to dest immediately.

        Using ncatted because it copies the file to the destination immediately
        too. The python lib does not do that.
        """
        process = subprocess.Popen([
            '/usr/bin/ncatted',
            '--attribute', 'processing_level,global,o,c,preliminary',
            '--attribute', 'processing_job,global,o,c,{uuid}'.format(uuid=self.processing_job),
            '--overwrite',
            '--history',
            '{0}'.format(self.source),
            '{0}'.format(self.dest)
        ], stderr=subprocess.PIPE)
        stderr = process.communicate()[1]
        if process.returncode:
            raise CommitError(stderr)

    # Alias to match NetCDF slang
    mark_preliminary = mark_unpublished

    def mark_published(self):
        """
        Mark NetCDF data published and move to dest immediately.

        Using ncatted because it copies the file to the destination immediately
        too. The python lib does not do that.
        """
        import datetime
        date_fmt = '%Y-%m-%dT%H:%M:%SZ'
        date_created = datetime.datetime.utcnow().strftime(date_fmt)
        date_modified = date_created

        command = [
            '/usr/bin/ncatted',
            '--attribute', 'processing_level,global,o,c,final',
            '--attribute', 'uuid,global,o,c,{uuid}'.format(
                uuid=self.processing_job),
            '--attribute', 'date_created,global,o,c,{date_created}'.format(
                date_created=date_created),
            '--attribute', 'date_modified,global,o,c,{date_modified}'.format(
                date_modified=date_modified),
            '--attribute', 'publisher_name,global,o,c,{user_name}'.format(
                user_name=self.user_name),
            '--attribute', 'publisher_email,global,o,c,{user_email}'.format(
                user_email=self.user_email),
            '--overwrite',
            '--history',
            '{0}'.format(self.source),
            '{0}'.format(self.dest)
        ]
        logger = logging.getLogger(self.__class__.__name__)
        logger.info('mark_published: %r' % ' '.join(command))
        process = subprocess.Popen(command, stderr=subprocess.PIPE)
        stderr = process.communicate()[1]
        if process.returncode:
            logger.error('stderr: %r' % stderr)
            raise CommitError(stderr)

    # Alias to match NetCDF slang
    mark_final = mark_published


class CommitKML(CommitBase):
    """
    Committing a KML file: copy to destination in /data/kml.

    Description:
        Committing is simply copying the file. It is not possible to set flags
        in the kml file which make a file published or final.
    Usage:
        To commit published:
        c = CommitKML('src.kml', 'dest.kml', published=True)
        c.commit() # Takes published=True into account
        c.mark_published()

        To commit unpublished:
        c = CommitKML('src.kml', 'dest.kml', published=False)
        c.commit() # Takes published=True into account
        c.mark_unpublished()
    """

    #def mark_unpublished(self):
    #    """
    #    remove file from /data/kml to unpublish
    #    """
    #    pass

    def mark_published(self):
        """
        Move kml data to dest, including directory structure.
        """
        copyfile(src=self.source, dst=self.dest)

