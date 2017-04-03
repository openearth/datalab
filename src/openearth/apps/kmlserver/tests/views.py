from django.conf import settings
from django.contrib.auth import login
from django.core.handlers.base import BaseHandler
from django.core.urlresolvers import reverse
from django.test import TestCase
import os
from openearth.apps.kmlserver.views import ListDirView

from django.test.client import RequestFactory
from openearth.apps.processing.tests.factories import StaffUserFactory


class RequestMock(RequestFactory):
    """
    Construct a generic request object, with session support.
    """
    csrf_cookie_value = 'foo'

    def request(self, **request):
        request = RequestFactory.request(self, **request)
        handler = BaseHandler()
        handler.load_middleware()

        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                 "request middleware returned a response")

        request.COOKIES[settings.CSRF_COOKIE_NAME] = self.csrf_cookie_value
        return request

    def post(self, *args, **kwargs):
        kwargs['data']['csrfmiddlewaretoken'] = self.csrf_cookie_value
        return super(RequestMock, self).post(*args, **kwargs)


class TestListDirView(TestCase):
    """
    Tests committing of individual kml files.

    Description:
        First tests publishing methods, next part is testing unpublish.
        Finally test commit method.
    """
    kml_file_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'kmlfiles'
    )
    rev_url = 'kmlserver'

    def initiate_view(self, user, kwargs={}):
        """
        Log user in, returns view instance.
        """
        request = RequestMock(user=user).get(
            path=reverse(self.rev_url),
            data=kwargs
        )
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        ldv = ListDirView(request=request, kwargs=kwargs)
        #ldv.dispatch(request=request, **kwargs)
        return ldv

    def fix_middleware(self):
        middleware = list(settings.MIDDLEWARE_CLASSES)
        idx = middleware.index('openearth.libs.middleware.LoginRequiredMiddleware')
        middleware.pop(idx)
        return middleware

    def test_is_safe_path(self):
        with self.settings(MIDDLEWARE_CLASSES=self.fix_middleware(), KML_FILE_DIR=self.kml_file_dir):
            user = StaffUserFactory()
            ldv = self.initiate_view(user)
            self.assertFalse(ldv.is_safe_path(os.path.join(self.kml_file_dir, '../')))
            self.assertFalse(ldv.is_safe_path(os.path.join(self.kml_file_dir, '/boot')))
            # http://en.wikipedia.org/wiki/Directory_traversal_attack
            # translates to ../
            self.assertFalse(ldv.is_safe_path(os.path.join(self.kml_file_dir, '%2e%2e/')))

    def test_list_dir_returns_dirs_only(self):
        """
        Test if list_dirs returns directories from KML_FILE_DIR
        """
        with self.settings(MIDDLEWARE_CLASSES=self.fix_middleware(), KML_FILE_DIR=self.kml_file_dir):
            user = StaffUserFactory()
            ldv = self.initiate_view(user)
            base_path = settings.KML_FILE_DIR
            print base_path
            ldv.cache_dir_content(base_path)
            dirs = ldv.list_dirs()
            print dirs
            self.assertGreaterEqual(len(dirs), 1)
            for dir_name in dirs:
                dir_path = os.path.join(base_path, dir_name)
                self.assertTrue(os.path.isdir(dir_path))

    # def test_dot_dir_return_return_404(self):
    #     """
    #     """
    #     with self.settings(MIDDLEWARE_CLASSES=self.fix_middleware()):
    #         user = StaffUserFactory()
    #         ldv = self.initiate_view(user)
    #         print ldv.get_context_data()
    #         print ldv.cache_dir_content(path='../')

    def test_build_absolute_root_path(self):
        with self.settings(MIDDLEWARE_CLASSES=self.fix_middleware(), KML_FILE_DIR=self.kml_file_dir):
            user = StaffUserFactory()
            ldv = self.initiate_view(user)
            base_path = settings.KML_FILE_DIR
            path = ldv.build_absolute_path('./')
            self.assertEqual(path, settings.KML_FILE_DIR)

    def test_build_absolute_root_path_subdir(self):
        subdir = 'subdir_1'
        fname = ''
        with self.settings(MIDDLEWARE_CLASSES=self.fix_middleware(), KML_FILE_DIR=self.kml_file_dir):
            user = StaffUserFactory()
            ldv = self.initiate_view(user, {'path': subdir})
            base_path = settings.KML_FILE_DIR
            path = ldv.build_absolute_path(
                os.path.join(subdir, fname)
            )
            self.assertEqual(
                os.path.realpath(path),
                os.path.realpath(os.path.join(
                    settings.KML_FILE_DIR,
                    subdir,
                    fname
                ))
            )

    def test_list_kml_returns_kmls(self):
        """
        Test if list_files files from KML_FILE_DIR
        """
        with self.settings(MIDDLEWARE_CLASSES=self.fix_middleware(), KML_FILE_DIR=self.kml_file_dir):
            user = StaffUserFactory()
            ldv = self.initiate_view(user)
            base_path = settings.KML_FILE_DIR
            ldv.cache_dir_content(base_path)
            dirs = ldv.list_files()
            self.assertGreaterEqual(len(dirs), 1)
            for dir_name in dirs:
                dir_path = os.path.join(base_path, dir_name)
                self.assertTrue(os.path.isfile(dir_path))

    def test_get_file_returns_x_accell_header(self):
        """
        Test if reaching a kml file returns a XACCELL header for nginx.

        Description:
            X-ACCELL offloads the downloading of files to nginx. Much faster.
        """
        with self.settings(MIDDLEWARE_CLASSES=self.fix_middleware(), KML_FILE_DIR=self.kml_file_dir):
            user = StaffUserFactory()
            kwargs = {'path': 'kmlfile_1.kml'}
            request = RequestMock(user=user).get(
                path=reverse(self.rev_url),
                data=kwargs
            )
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            ldv = ListDirView(request=request, kwargs=kwargs)
            #ldv.dispatch(request=request, **kwargs)
            resp = ldv.get(request=request, **kwargs)
            self.assertEqual(resp['X-Accel-Redirect'], '/secure_kml/kmlfile_1.kml')
            self.assertNotIn('Content-Type', resp._headers)

