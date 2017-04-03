from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from openearth import views
from openearth.apps.kmlserver.views import ListDirView
from libs.auth import LDAPSetPasswordForm, LDAPPasswordChangeForm, LDAPPasswordResetForm
from ws4redis.wsgi_server import WebsocketWSGIServer
from apps.script_execution_manager.wsgi_server import patched_call
import logging


logger = logging.getLogger(__name__)

#TODO Find a better location to pacth WebsocketWSGIServer.__call__
logger.debug('Patching "ws4redis.wsgi_server.WebsocketWSGIServer.__call__"...')
WebsocketWSGIServer.__call__ = patched_call

admin.autodiscover()

urlpatterns = patterns(
    '',

    url(r'^admin/', include(admin.site.urls)),
    url(r'^kmlserver/', include('openearth.apps.kmlserver.urls')),
    url(r'^documentation', include('openearth.apps.documentation.urls')),
    url(r'^tags_input/', include('tags_input.urls', namespace='tags_input')),
    url(r'^', include('openearth.urls')),
    url(r'^', include('cms.urls')),
    url(r'^', include('filer.server.urls')),
)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
        url(r'^smedia/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.FILER_STORAGES['private']['main']['OPTIONS']['location'],
        }),
        # url(r'^kml/(?P<path>.*)$', 'django.views.static.serve', {
        #     'document_root': settings.FILER_STORAGES['private']['kml']['OPTIONS']['location'],
        #     'show_indexes': True
        # }),
   )

