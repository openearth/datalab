from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from django.views.generic import TemplateView
import os
import urllib


class ListDirView(TemplateView):
    http_method_names = ['get']
    template_name = 'index.html'
    dir_content = []

    def build_absolute_path(self, path):
        """
        Builds absolute path from given path and KML_FILE_DIR setting.

        Arguments:
            path String with path. eg /myfiles/
        Returns:
            absolute path
        """
        decoded_path = urllib.unquote(path).decode('utf8')
        path = os.path.join(settings.KML_FILE_DIR, decoded_path)
        return os.path.realpath(path)
    #
    # def get_file_owner(self, abs_path):
    #     """
    #     returns the name of the owner of the file.
    #     """
    #     return getpwuid(os.stat(abs_path).st_uid).pw_name

    def is_safe_path(self, rel_path):
        """
        Checks if path is within KML_FILE_DIR.
        Returns:
            Boolean True if path is safe, False if unsafe.
        """
        abs_path = self.build_absolute_path(os.path.join(
            self.kwargs.get('path') or './',
            rel_path
        ))
        # process_user = getpwuid(os.geteuid()).pw_name
        return all([
            # Path to be retrieved should start with KML_FILE_DIR
            abs_path.startswith(settings.KML_FILE_DIR),
            # Make sure only files owned by current process are safe
            #self.get_file_owner(abs_path) == process_user #TODO?
        ])

    def cache_dir_content(self, path):
        """
        Store content in self.dir_content

        Arguments:
            path is a string with a relative path to the KML_FILE_DIR setting.

        Description:
            self.dir_content is used by get_dirs and get_files.
        """
        self.dir_content = os.listdir(self.build_absolute_path(path))

    def list_dirs(self):
        def isdir(item):
            return os.path.isdir(self.build_absolute_path(os.path.join(
                self.kwargs.get('path') or './',
                item
            )))

        return filter(isdir, self.dir_content)

    def list_files(self):
        """
        Return list of kml files.
        """
        def isfile(item):
            """
            Check if item is a file and if it ends in KML_FILE_EXTS.

            Returns:
                Boolean
            """
            fpath = self.build_absolute_path(os.path.join(
                self.kwargs.get('path') or './',
                item
            ))
            return os.path.isfile(fpath) \
                   and os.path.splitext(fpath)[1] in settings.KML_FILE_EXTS

        return filter(isfile, self.dir_content)

    def get_context_data(self, **kwargs):
        kwargs = super(ListDirView, self).get_context_data(**kwargs)
        kwargs['directories'] = self.list_dirs()
        kwargs['files'] = self.list_files()
        kwargs['fancy_path'] = self.kwargs.get('path', './') or './'
        if not self.kwargs.get('path'):
            kwargs['dir_prefix'] = reverse('kmlserver')
        else:
            args = ['{0}/'.format(self.kwargs.get('path'))]
            kwargs['dir_prefix'] = reverse('kmlserver', args=args)

        kwargs['prev_dir'] = os.path.realpath(
            os.path.join(kwargs['dir_prefix'], '..')
        )
        return kwargs

    def get(self, request, *args, **kwargs):
        path = self.kwargs.get('path', './') or './'
        errstr = 'File or directory "{0}" is not available.'
        if not self.is_safe_path(path):
            raise Http404(errstr.format(path))

        abs_path = self.build_absolute_path(path)
        if not os.path.exists(abs_path):
            raise Http404(errstr.format(path))

        # has permission
        #if not self.has_read_permission(path):
        #    raise PermissionDenied(errstr.format(path))

        if os.path.isdir(abs_path):
            self.cache_dir_content(path)
            return super(ListDirView, self).get(request, *args, **kwargs)
        if os.path.isfile(abs_path):
            url_root = getattr(settings, 'KML_NGINX_LOCATION')
            response = HttpResponse()
            # Remove the content type to let Nginx figure it out
            del response['Content-Type']
            response['X-Accel-Redirect'] = '{0}/{1}'.format(url_root, path)
            return response
        else:
            raise PermissionDenied()


class KmlView(TemplateView):
    """
    Loads the selected kml file into the google earth browser plugin.
    """
    http_method_names = ['get']
    template_name = 'kml_view.html'
