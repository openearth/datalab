from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings
from os.path import dirname, join, normpath, abspath

if not hasattr(os.environ, 'SECRET_KEY'):
    from openearth.libs.environment import read_env
    read_env()

# set the default Django settings module for the 'celery' program.
if not hasattr(os.environ, 'DJANGO_SETTINGS_MODULE') or settings.DEBUG:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'openearth.settings.dev')

#broker = "redis+socket:///var/run/redis/redis.sock/"
app = Celery('openearth', include=['openearth.libs.tasks'])

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.update(
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_TASK_SERIALIZER='json',
    CELERY_RESULT_SERIALIZER='json',
)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


def get_celery_worker_status():
    ERROR_KEY = "ERROR"
    try:
        from celery.task.control import inspect
        insp = inspect()
        d = insp.stats()
        if not d:
            d = { ERROR_KEY: 'No running Celery workers were found.' }
    except IOError as e:
        from errno import errorcode
        msg = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
            msg += ' Check that the RabbitMQ server is running.'
        d = { ERROR_KEY: msg }
    except ImportError as e:
        d = { ERROR_KEY: str(e)}
    return d