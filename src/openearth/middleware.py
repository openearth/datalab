from django.conf import settings
from re import compile


class SSOMiddleware(object):
    def process_response(self, request, response):
        if request.path_info.startswith('/auth/'):
            for cookie in response.cookies.keys():
                if cookie != 'sessionid':
                    response.cookies.pop(cookie)

        return response

