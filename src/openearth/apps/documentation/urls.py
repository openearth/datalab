from django.conf.urls import patterns, include, url
from openearth.apps.documentation.views import DocumentationOverView

urlpatterns = patterns('',
    url(r'^$', DocumentationOverView.as_view(), name='document_index')
)
