from django.conf.urls import patterns, include, url
import views

env_patterns = patterns(
    '',
    url(r'jobs/$', views.JobListView.as_view(), name='jobs'),
    url(r'repo/$', views.RepoRevisionsView.as_view(), name='repo_revisions'),
    url(r'scripts/$', views.ScriptsView.as_view(), name='scripts'),
    url(r'scripts/(?P<script>.+)$', views.ScriptRevisionsView.as_view(), name='script_revisions'),
    url(r'open_earth_revisions/(?P<extension>.*)$', views.OpenEarthRevisionsView.as_view(), name='open_earth_revisions'),
    url(r'job/create/$', views.JobCreateView.as_view(), name='job_create'),
    url(r'job/(?P<uuid>[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12})/$', views.JobDetailView.as_view(), name='job_detail'),
    url(r'job/(?P<uuid>[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12})/edit/$', views.JobUpdateView.as_view(), name='job_update'),
)

urlpatterns = patterns(
    '',
    url(r'^$', views.EnvironmentListView.as_view(), name='environment'),
    url(r'^create/$', views.EnvironmentCreateView.as_view(), name='environment_create'),
    url(r'^(?P<pk>\d+)/$', views.EnvironmentDetailView.as_view(), name='environment_detail'),
    url(r'^(?P<pk>\d+)/edit/$', views.EnvironmentUpdateView.as_view(), name='environment_update'),
    url(r'^(?P<env>\d+)/', include(env_patterns)),
)
