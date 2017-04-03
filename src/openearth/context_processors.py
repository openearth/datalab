def view_name(request):
    from django.core.urlresolvers import resolve
    return {'view_name': lambda: resolve(request.path_info).url_name}


def svn_url(request):
    from django.conf import settings
    return {'svn_url': settings.ENVIRONMENT_SVN_URL}

