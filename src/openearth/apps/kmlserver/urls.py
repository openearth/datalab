from django.conf.urls import patterns, include, url
from .views import ListDirView, KmlView

urlpatterns = patterns('',
    url(r'^kmlviewer/(?P<path>.+)$', KmlView.as_view(), name='kmlviewer'),
    url(r'^((?P<path>.+))?$', ListDirView.as_view(), name='kmlserver'),
)