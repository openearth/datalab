"""
WSGI config for openearth project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
change log:
2-1-2014 : environment setting voor LDAPPWD ingesteld voor test.
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openearth.settings.prod")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
