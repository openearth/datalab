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

urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name="homepage.html"), name='homepage'),
    url(r'^about/$', TemplateView.as_view(template_name="about.html"), name='about'),
    url(r'^helpdesk/$', TemplateView.as_view(template_name="helpdesk.html"), name='helpdesk'),
    url(r'^environment[s]?/', include('openearth.apps.processing.urls')),
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^auth/$', views.AuthView.as_view(), name='auth'),
    url(r'^logout/$', 'openearth.views.logout_view', name='logout'),
    url(r'^websocket/', views.WebsocketView.as_view(), name='websocket'),
)

urlpatterns += patterns(
    'django.contrib.auth.views',
    url(r'^user/password/reset/$', 'password_reset',
        {'post_reset_redirect': '/user/password/reset/send/',
         'password_reset_form': LDAPPasswordResetForm},
        name="password_reset"),
    (r'^user/password/reset/send/$', 'password_reset_done'),
    (r'^user/password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
     'password_reset_confirm',
     {'post_reset_redirect': '/user/password/done/', 'set_password_form':
      LDAPSetPasswordForm}),
    (r'^user/password/done/$',
     'password_reset_complete'),
    url(r'^user/password/change/$', 'password_change',
        {'post_change_redirect': '/user/password/change/done/',
         'password_change_form': LDAPPasswordChangeForm},
        name="password_change"),
    url(r'^user/password/change/done/$',
        'password_change_done'),
)

