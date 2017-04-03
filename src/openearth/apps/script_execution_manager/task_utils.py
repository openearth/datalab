from __future__ import unicode_literals
from django.conf import settings
from filer.models import File
import os
import time
import redis
import re
from celery.utils.log import get_task_logger
from ws4redis import settings as redis_settings
from django.core.files import File as DjangoFile

from .container import LibVirtDomain
from .container import LibVirtDomainException


_redis_connection = redis.StrictRedis(**redis_settings.WS4REDIS_CONNECTION)
logger = get_task_logger(__name__)


def wait_for_ip(lv):
    """
    Tries to get IP until domain has one, or max_tries is reached.
    """
    logger.info('Getting ip for mac address "{0}"...'.format(lv.network_mac_address))
    max_tries = 40
    while max_tries:
        time.sleep(1)
        try:
            ip = lv.get_ip_address()
            logger.info('Got ip "{0}"'.format(ip))
            return ip
        except LibVirtDomainException, e:
            logger.info('{0}. {1} tries left.'.format(unicode(e), max_tries))
        max_tries -= 1

    raise ValueError('Tried a few times, but no IP found in "{0}."'.format(
        lv.dnsmasq_leases
    ))


def cleanup(uuid, image):
    """
    Cleans up the environment for the task.

    Tries to destroy the libvirt domain.
    TODO: manually check if image is gone. perhaps undo dhcp lease etc.

    Arguments:
        uuid: uuid of job as string.
        image: name of image used to run task.
    """
    lv = LibVirtDomain(uuid=uuid, image=image)
    try:
        logger.info("Destroying domain '{0}'".format(lv.get_instance_name()))
        lv.destroy()
    except LibVirtDomainException, e:
        logger.warn('Cannot destroy domain: {0}'.format(e.message))


def find_files(path, extension):
    """
    Finds files with extension, append them to job result.

    Arguments:
        job: a ProcessingJob object.
        path: path to directoy which contains results.
            eg: /data/containers/results-<uuid>
        extension: .nc, .csv, .whatever. (dot included!)

    Returns:
        a list of filepaths all having given extension
    """
    re_ext = re.compile('.*\{0}$'.format(extension))
    def add(filename):
        file_path = os.path.join(path, filename)
        if re_ext.match(filename):
            return file_path

    return filter(None, map(add, os.listdir(path)))


def add_file_to_job_result(job, file_path):
    """
    Append file_path to job.processing_result.

    Arguments:
        job: A ProcessingJob object
        file_path: absolute path to file. eg:
        /data/containers/results-<uuid>/file.nc
    """
    filename = os.path.basename(file_path)
    file_obj = DjangoFile(open(file_path, 'r'), name=filename)
    filer_file = File.objects.create(
        owner=job.environment.author,
        original_filename=filename,
        file=file_obj
    )
    return job.processing_result.create(file=filer_file)


def append_files(namespace):
    """
    Append all files to a job as ProcessingJobResult.

    Currently adds: .nc .m .txt .log .csv .kml .kmz .png files.

    Arguments:
        namespace: uuid string of job.
    """
    from openearth.apps.processing.models import ProcessingJob
    job = ProcessingJob.objects.get(pk=namespace)
    results_dir = os.path.join(
        settings.CONTAINER['base_dir'],
        'results-{0}'.format(namespace)
    )
    logger.info("Collecting results files from '{0}'".format(results_dir))
    file_exts = ['.nc', '.m', '.txt', '.log', '.csv', '.kml', '.kmz', '.png']

    for ext in file_exts:
        result_files = find_files(path=results_dir, extension=ext)
        logger.debug("Found files: ".format(result_files))
        logger.debug(type(result_files))
        for f in result_files:
            logger.debug('adding file: {0}'.format(f))
            add_file_to_job_result(job=job, file_path=f)

def create_results_dir(uuid):
    """
    Create results dir in /data/containers/results-<uuid> if it doesnt exist.

    Sets mode to 777 for now.
    """
    logger.info('Fixme: set results dir mode=0777 might not be a good idea...')

    results_dir = os.path.join(
        settings.CONTAINER['base_dir'],
        'results-{0}'.format(uuid)
    )
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    os.chmod(results_dir, 0777)
    return results_dir
