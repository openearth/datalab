from __future__ import unicode_literals
from django.conf import settings
import logging
import os
from celery.utils.log import get_task_logger
from celery.signals import before_task_publish, after_task_publish, \
    task_prerun, task_postrun, task_retry, task_success, task_failure, task_revoked
import time
from .container import LibVirtDomain
from .exec_wrapper import ExecWrapper, mark_secret
from .logger import WebsocketLoggerHandler
from openearth.apps.script_execution_manager.commit_worker import CommitNetCDF, \
    CommitError, CommitKML, CommitCSV
from openearth.celery import app
from .task_utils import append_files, cleanup, wait_for_ip, create_results_dir
logger = get_task_logger(__name__)
from django.core.exceptions import ObjectDoesNotExist


def setup_logger(username, namespace, logfile_path):
    """
    Add child logger to main logger object; specific for each task.

    Then add redis handler to that child logger. Every task gets its own logger.
    This avoids multiple tasks having multiple redis_handlers; and thus sending
    it's log to other subscribers too.

    Arguments:
        username
        namespace String with UUID (key in redis)
        logfile_path: String with path to logfile.
            (eg: /data/containers/instance-<uuid>/logfile.log)

    Returns:
        logger object, which should be used for thread-safe websocket logging.

    Future:
        this probably can be done better. We could put logger = get_task_logger
        on top of this file and in this function logger.get_child(namespace).
        Then we append a logger. Then its probably not required anymore to
        remove the other handler.

    TODO:
        add file handler
        handler = logging.FileHandler('tasks.log')
        formatter = logging.Formatter(logging.BASIC_FORMAT) # you may want to
        customize this.
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    """
    child_logger = logger.getChild(str(namespace))
    config = {
        'username': username,
        'namespace': namespace
    }
    redis_handler = WebsocketLoggerHandler(
        config=config,
        channels=['subscribe-user', 'publish-user']
    )
    file_handler = logging.FileHandler(logfile_path)
    formatter = logging.Formatter(
        fmt="[%(levelname)s] %(asctime)s : %(message)s",
    )
    # We could check if the logger already exists, but it might have been
    # defined elsewhere. In that case, the loggers might not have been added.
    # Therefore we should check if the redis and file handlers already exist.
    # handlers are in here. Check if type of redis and file_handler are already
    # in there.

    handler_types = [type(h) for h in child_logger.handlers]
    if not WebsocketLoggerHandler in handler_types:
        redis_handler.setFormatter(formatter)
        child_logger.addHandler(redis_handler)

    if not logging.FileHandler in handler_types:
        file_handler.setFormatter(formatter)
        child_logger.addHandler(file_handler)

    child_logger.setLevel(logging.DEBUG)
    return child_logger


@app.task()
def run_script(namespace, username, image, interpreter, script_name, svn_url,
               svn_script_path, revision, script_revision, open_earth_tools,
               open_earth_revision):
    """
    Start container, ssh into it and run script.

    TODO: a uuid/namespace probably is enough as an argument. (job object is
        required anyways) To eliminate the requirement of a job object (and thus
        a database connection on every server, use the return result and camera)

    TODO: massive rewrite and cleanup of this task/module. Commands should be
        made configurable, when defining an container in the admin. EG: the
        matlab container, in addition to checking out the datasets, should also
        checkout <svn url>, run a matlab command, .
        The python container should have an additional command which runs pip
        freeze. Currently all these commands are hardcoded.

    Arguments:
        namespace: uuid of ProcessingJob
        image: filename of image in containers dir.
        interpreter: TBD
        script_name: TBD
        open_earth_tools: Boolean which indicates if open_earth_tools have to be
            checked out.

    """
    from openearth.apps.processing.models import ProcessingJob
    obj = ProcessingJob.objects.get(uuid=namespace)
    obj.set_status('RUNNING')

    results_dir = create_results_dir(uuid=namespace)
    log_file_path = os.path.join(results_dir, 'run.log')
    logger = setup_logger(
        username=username, namespace=namespace, logfile_path=log_file_path
    )
    logger.info('Defining processing environment')
    lv = LibVirtDomain(
        uuid=namespace,
        image=image,
        external_logger=logger
    )
    try:
        logger.info('Launching processing environment')
        lv.create()
        ip = wait_for_ip(lv)
        logger.info('Wait until SSH server is started in container')
        time.sleep(15)

        commands = []
        commands.append([
            '/usr/bin/svn', 'co', svn_url, '/home/worker/svn',
            '--revision', str(revision),
            '--username', mark_secret(settings.ENVIRONMENT_SVN_USERNAME),
            '--password', mark_secret(settings.ENVIRONMENT_SVN_PASSWORD),
             '--non-interactive', '--trust-server-cert'
        ])

        if script_revision and script_revision != revision:
            commands.append([
                '/usr/bin/svn', 'co', svn_url + svn_script_path,
                '/home/worker/svn/' + svn_script_path,
                '--revision', str(script_revision),
                '--username', mark_secret(settings.ENVIRONMENT_SVN_USERNAME),
                '--password', mark_secret(settings.ENVIRONMENT_SVN_PASSWORD),
                '--non-interactive', '--trust-server-cert'
            ])
        commands.append([
            '/usr/bin/yum', 'list', 'installed', '>',
            '/home/worker/results/installed_rpms.txt'
        ])
        commands.append([
            '/opt/python2.7/bin/pip', 'freeze', '>',
            '/home/worker/results/installed_python_packages.txt'
        ])
        #[interpreter, '/home/worker/svn/scripts/{0}'.format(script_name)]
        # Should be (A migration plan should be made as well. (do it
        # manually?)):
        if open_earth_tools:
            command_parts = [
                '/usr/bin/svn', 'co', '--non-interactive',
                '--trust-server-cert',
            ]
            if open_earth_revision:
                command_parts += [
                    '--revision', str(open_earth_tools),
                ]

            commands.append(command_parts + [
                '--username', mark_secret(
                    settings.OPEN_EARTH_TOOLS_MATLAB_USERNAME),
                '--password', mark_secret(
                    settings.OPEN_EARTH_TOOLS_MATLAB_PASSWORD),
                settings.OPEN_EARTH_TOOLS_MATLAB_URL,
                settings.OPEN_EARTH_TOOLS_MATLAB_PATH,
            ])
            commands.append(command_parts + [
                '--username', mark_secret(
                    settings.OPEN_EARTH_TOOLS_PYTHON_USERNAME),
                '--password', mark_secret(
                    settings.OPEN_EARTH_TOOLS_PYTHON_PASSWORD),
                settings.OPEN_EARTH_TOOLS_PYTHON_URL,
                settings.OPEN_EARTH_TOOLS_PYTHON_PATH,
            ])
        # oe tools: https://svn.oss.deltares.nl/repos/openearthtools/trunk/matlab/
        #/opt/matlab/bin/matlab  -nosplash -nodisplay -r "run('oetsettings');run('{script_path}');exit"
        commands.append([interpreter.format(script_path='/home/worker/svn/scripts/{0}'.format(script_name))])

        home_dir = os.path.expanduser("~")
        ssh_command = [
            '/usr/bin/ssh',
            "-oStrictHostKeyChecking=no",
            "-oUserKnownHostsFile=/dev/null",
            "-i", "{0}/.ssh/id_rsa_worker".format(home_dir),
            "worker@{0}".format(ip)
        ]
        for c in commands:
            logger.info('Executing command "{0}"'.format(c))
            command = ssh_command + c
            ew = ExecWrapper(
                command=command,
            )
            for stdout_stderr in ew.start_process():
                logger.info(stdout_stderr)
    except Exception as e:
        logger.error(str(e))
        raise e

    logger.info('Cleaning image')
    cleanup(uuid=namespace, image=image)
    logger.info('Appending files to Job')
    append_files(namespace=namespace)
    logger.info('Done!')
    return True


@before_task_publish.connect()
def after_task_publish_handler(sender=None, body=None, **kwargs):
    if sender == 'openearth.apps.script_execution_manager.tasks.run_script':
        from openearth.apps.processing.models import ProcessingJob
        try:
            obj = ProcessingJob.objects.get(uuid=body['id'])
            obj.set_status('SCHEDULED')
        except ObjectDoesNotExist, e:
            # no object found, no reason to set status. Ignore
            pass


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    from openearth.apps.processing.models import ProcessingJob
    try:
        obj = ProcessingJob.objects.get(uuid=task_id)
        obj.set_status(task.AsyncResult(task.request.id).state)
    except ObjectDoesNotExist, e:
        # no object found, no reason to set status. Ignore
        pass


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    from openearth.apps.processing.models import ProcessingJob
    print result


@task_revoked.connect
# sender filtering in decorator has a bug: http://stackoverflow.com/a/19010186
# @task_failure.connect(sender='openearth.apps.script_execution_manager.tasks.run_script')
def task_revoked_handler(request, sender, *args, **kwargs):
    # called twice, for some reason. Probably because sender is not correctly
    # specified in the decorator. --> not called twice. Logging thing.
    results_dir = create_results_dir(uuid=request.kwargs['namespace'])
    log_file_path = os.path.join(results_dir, 'run.log')
    logger = setup_logger(
        username=request.kwargs['username'],
        namespace=request.kwargs['namespace'],
        logfile_path=log_file_path
    )
    try:
        from openearth.apps.processing.models import ProcessingJob
        obj = ProcessingJob.objects.get(uuid=request.task_id)
        obj.set_status('REVOKED')
    except ObjectDoesNotExist, e:
        pass

    logger.warn("Task '{0}' REVOKED, cleaning environment.".format(request.task_id))
    logger.warn("Sender: {0}".format(sender.name))
    logger.warn("Request.name: {0}".format(request.name))
    try:
        append_files(request.task_id)
    except Exception, e:
        logger.error('Major error: {0}'.format(str(e)))
        logger.error('Continue to force cleanup. ')
    try:
        logger.info("Destroying image")
        cleanup(uuid=request.task_id, image=request.kwargs['image'])
    except Exception, e:
        logger.exception('Error while doing cleanup: {0} {1}'.format(
            type(e).__name__, str(e))
        )
    logger.info("Job '{0}' finished.".format(request.task_id))


# sender filtering in decorator has a bug: http://stackoverflow.com/a/19010186
# @task_failure.connect(sender='src.openearth.apps.script_execution_manager.tasks.exception')
@task_failure.connect
def task_failure_handler(sender, task_id, *args, **kwargs):
    """
    Cleanup image and add files which where found.

    TODO: make sure this is run on worker host, with a subtask
        'Signatures are often nicknamed 'subtasks' because they describe **a
        task** to be called **within a task**.' append_files is a problem
        though. the files have to be copied to the main host first. ssh-copy in
        a subtask?

    This is what comes in:
    {
        'exception': TypeError('info() takes at least 2 arguments (1 given)',),
        'traceback': <traceback object at 0x40e54d0>,
        'sender': <@task: openearth.apps.script_execution_manager.tasks.run_script of openearth:0x28aee90>,
        'task_id': u'2038c7de-b71d-47be-9f8d-34b0ba49e587',
        'signal': <Signal: Signal>,
        'args': [],
        'kwargs': {
            u'username': u'admin',
            u'image': u'/data/containers/centos-6-x86_64',
            u'namespace': u'2038c7de-b71d-47be-9f8d-34b0ba49e587',
            u'svn_url': u'https://198.51.100.3/repos/openearth/demo_dataset/',
            u'script_name': u'create_results.py',
            u'interpreter': u'/opt/python2.7/bin/python'},
            'einfo': <ExceptionInfo: TypeError('info() takes at least 2 arguments (1 given)',)>
        }
    }
    """
    obj = None
    results_dir = create_results_dir(uuid=kwargs['kwargs']['namespace'])
    log_file_path = os.path.join(results_dir, 'run.log')
    namespace = kwargs['kwargs']['namespace']
    logger = setup_logger(
        username=kwargs['kwargs']['username'],
        namespace=namespace,
        logfile_path=log_file_path
    )
    from openearth.apps.processing.models import ProcessingJob
    try:
        obj = ProcessingJob.objects.get(uuid=namespace)
        obj.set_status('FAILURE')
    except ObjectDoesNotExist, e:
        logger.warn('ProcessingJob object with uuid "{0}" not found.'.format(
            namespace
        ))
        logger.error(e)

    logger.info('sender: {0}'.format(sender))
    logger.warn("Task '{0}' FAILED, cleaning environment.".format(task_id))
    logger.warn("Running failure hander for id '{0}'".format(namespace))
    logger.warn("Sender: {0}".format(sender.name))
    try:
        append_files(namespace)
    except Exception, e:
        logger.error('Major error: {0}'.format(str(e)))
        logger.error('Continue to force cleanup. ')
    if obj:
        try:
            image = obj.environment.libvirt_image
            logger.info("Destroying image 'instance-{0}'".format(namespace))
            # cleanup(uuid=task_id, image=kwargs['kwargs']['image'])
            cleanup(uuid=namespace, image=image)
        except Exception, e:
            logger.exception('Error while doing cleanup: {0} {1}'.format(
                type(e).__name__, str(e))
            )
    logger.info("Task failure handler '{0}' finished.".format(task_id))
    logger.info("Job '{0}' FAILED.".format(kwargs['kwargs']['namespace']))


@app.task()
def commit(prev_task_result, namespace, username, user_name=None, user_email=None):
    """
    When container scripts are done, commit results to DB or OPeNDAP dir.

    This task loops over the files, appended to ProcessingJob object. When doing
    so it figures out if it's a nc or a csv file. netcdfs will be copied to the
    opendap dir. The netcdf processing_level argument will be updated to final.

    This task has to be run on the host which has the file servers and db
    servers.

    TODO: CSV
    2: parse csv file in to memory
    3: make sure its unpublished (or do this while inserting into db)
    4: put stuff in db
    """
    from openearth.apps.processing.models import ProcessingJob
    # Logger has been set up in run_script task.
    results_dir = create_results_dir(uuid=namespace)
    log_file_path = os.path.join(results_dir, 'run.log')
    logger = setup_logger(
        username=username,
        namespace=namespace,
        logfile_path=log_file_path
    )
    logger.info('Starting commit worker for: {0}'.format(namespace))
    job = ProcessingJob.objects.get(pk=namespace)

    for result in job.processing_result.all():
        file_ext = os.path.splitext(result.file.path)[1]
        filename = os.path.basename(result.file.path)
        logger.info('Try to commit file: {0}'.format(filename))
        if file_ext == '.nc':
            dest_dir = os.path.join(
                settings.OPENDAP_DATA_DIR,
                job.environment.repo
            )
            dest = os.path.join(dest_dir, filename)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            logger.info('Adding file "{0}" to "{1}"'.format(
                filename,
                dest
            ))
            cncdf = CommitNetCDF(
                source=result.file.path,
                dest=dest,
                processing_job=job.uuid,
                published=True,
                user_email=user_email,
                user_name=user_name
            )
            try:
                cncdf.commit()
            except CommitError, e:
                logger.warn(
                    'An error occurred while processing the nc file. '
                    '{0}'.format(e)
                )
        elif file_ext == '.csv': # Should be merged w orm_commit_worker branch
            logger.info('Adding file "{0}" to database'.format(filename))
            ccsv = CommitCSV(
                source=result.file.path,
                processing_job=job,
                published=True
            )
            try:
                ccsv.commit()
            except CommitError, e:
                print e
                logger.warn(
                    'An error occurred while processing the CSV file. '
                    '{0}'.format(e)
                )
                # TODO: make results-directory traversal recursive. Integrate
                # for netcdf as well.
        if file_ext in settings.KML_FILE_EXTS:
            dest_dir = os.path.join(
                settings.KML_FILE_DIR,
                job.environment.repo
            )
            logger.info('Adding file "{0}" to "{1}"'.format(filename, dest_dir))
            dest = os.path.join(dest_dir, filename)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            ckml = CommitKML(
                source=result.file.path,
                dest=dest,
                processing_job=job,
                published=True
            )
            ckml.commit()
    logger.info('Finished committing files.')
    job.set_status('FINISHED')
    return job.uuid


@app.task()
def logger_task():
    """
    Task to figure out thread safe logging to websocket.
    """
    from uuid import uuid1
    namespace = uuid1()
    logger = get_task_logger(__name__)
    config = {
        'username': 'username',
        'namespace': namespace
    }
    redis_handler = WebsocketLoggerHandler(config=config, channels=['subscribe-user', 'publish-user'])
    # formatter = logging.Formatter(
    #     fmt="[%(levelname)s] %(asctime)s : %(message)s",
    # )
    # redis_handler.setFormatter(formatter)
    logger.addHandler(redis_handler)
    logger.setLevel(logging.DEBUG)
    # print 'logging test'
    logger.info('logger.handlers: {0}'.format(logger.handlers))
    handlers = logger.handlers[1:]
    for h in handlers:
        if not h is redis_handler:
            logger.info('Removing.......... {0}'.format(h))
            logger.removeHandler(h)
        else:
            logger.info('Equal: {0} - {1}'.format(h, redis_handler))
    logger.info('!!########!! slept 3 secs, removed a handler, check if altered: {0}'.format(logger.handlers))
