"""
WSGI config for openearth project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
change log:
2-1-2014 : environment setting voor LDAPPWD ingesteld voor test.
"""

import os
import gevent.monkey
import redis.connection
redis.connection.socket = gevent.socket
os.environ.update(DJANGO_SETTINGS_MODULE='openearth.settings.prod')
from ws4redis.uwsgi_runserver import uWSGIWebsocketServer
from apps.script_execution_manager.wsgi_server import patched_call
uWSGIWebsocketServer.__call__ = patched_call
application = uWSGIWebsocketServer()



