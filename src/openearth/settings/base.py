"""
Django settings for openearth project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import ldap
from sys import path
import os
from datetime import timedelta
from django_auth_ldap.config import LDAPSearch, PosixGroupType
from os.path import abspath, basename, dirname, join, normpath
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning,
                        module='simplejson')


########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# Site ID
SITE_ID = 1

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# SECURITY WARNING: don't run with debug turned on in production!
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## AUTHENTICATION/AUTHORIZATION CONFIGURATION
LOGIN_REDIRECT_URL = '/'

LOGIN_URL = '/login/'

LOGIN_EXEMPT_URLS = (
    r'^$',
    r'^about/$',
    r'^helpdesk/$',
    r'^login/$',
    r'^user/password/reset/$',
    r'^user/password/reset/send/$',
    r'^user/password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
    r'^user/password/reset/done/$',
    r'^user/password/change/$',
    r'^user/password/change/done/$',
    r'^auth/$',
)

LDAP_DC_FIRST = os.environ.get('LDAP_DC_FIRST')
LDAP_DC_SECOND = os.environ.get('LDAP_DC_SECOND')
LDAP_ADMIN_PASSWD = os.environ.get('LDAP_ADMIN_PASSWD')

# LDAP configuration
AUTH_LDAP_OU = 'people'
AUTH_LDAP_GROUPS_OU = 'group'
AUTH_LDAP_ALWAYS_UPDATE_USER = True
AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = True
AUTH_LDAP_BIND_DN = "cn=admin,dc=%s,dc=%s"%(LDAP_DC_FIRST,LDAP_DC_SECOND)
AUTH_LDAP_BIND_PASSWORD = LDAP_ADMIN_PASSWD
AUTH_LDAP_CACHE_GROUPS = True
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_GLOBAL_OPTIONS = {
    ldap.OPT_X_TLS_REQUIRE_CERT: False,
    ldap.OPT_REFERRALS: False
}
AUTH_LDAP_GROUP_CACHE_TIMEOUT = 1
AUTH_LDAP_GROUP_TYPE = PosixGroupType()
AUTH_LDAP_MIRROR_GROUPS = True
AUTH_LDAP_SERVER_URI = "ldap://localhost:389"
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail"
}
AUTH_LDAP_USER_FLAGS_BY_GROUP = {}

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "dc=%s,dc=%s"%(LDAP_DC_FIRST,LDAP_DC_SECOND),
    ldap.SCOPE_SUBTREE,
    "(uid=%(user)s)"
)
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "ou=group,dc=%s,dc=%s"%(LDAP_DC_FIRST,LDAP_DC_SECOND),
    ldap.SCOPE_SUBTREE,
    "(objectClass=organizationalPerson)"
)

############################## django-auth-ldap ##############################
if DEBUG:
    import logging, logging.handlers
    logfile = "/srv/openearth/log/django-ldap-debug.log"
    my_logger = logging.getLogger('django_auth_ldap')
    my_logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
       logfile, maxBytes=1024 * 500, backupCount=5)

    my_logger.addHandler(handler)
############################ end django-auth-ldap ############################

AUTHENTICATION_BACKENDS = (
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)

########## END AUTHENTICATION/AUTHORIZATION CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '%s' % os.environ.get('DJANGO_DATABASE_NAME', SITE_NAME),
        'USER': '%s' % os.environ.get('DJANGO_DATABASE_USER', SITE_NAME),
        'PASSWORD': '%s' % os.environ.get('DJANGO_DATABASE_PASS', SITE_NAME),
        'PORT': '',
        'HOST': '',
    }
}
########## END DATABASE CONFIGURATION


########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'Europe/Amsterdam'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

gettext = lambda s: s

LANGUAGES = (
    ('en-us', gettext('English')),
)

CMS_LANGUAGES = {
    'default': {
        'fallbacks': ['en'],
        'redirect_on_fallback': True,
        'public': True,
        'hide_untranslated': False,
    },
}

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION

########## SERVER_URL CONFIGURATION
SERVER_NAME = os.environ.get('SERVER_NAME')
########## END SERVER_URL CONFIGURATION

########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(dirname(SITE_ROOT), 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(dirname(SITE_ROOT), 'static'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(dirname(SITE_ROOT), 'assets')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = os.environ.get('SECRET_KEY')
########## END SECRET CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(DJANGO_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'openearth.context_processors.view_name',
    'openearth.context_processors.svn_url',

    'sekizai.context_processors.sekizai',
    'cms.context_processors.cms_settings',
    'cms_extension.processors.site_processor',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
TEMPLATE_DIRS = (
    normpath(join(DJANGO_ROOT, 'templates')),
)

CMS_TEMPLATES = (
    ('base.html', 'Base template'),
)
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',

    # Use GZip compression to reduce bandwidth. #TODO let the webserver handle this
    'django.middleware.gzip.GZipMiddleware',

    # Should be before the csrf middleware
    'openearth.middleware.SSOMiddleware',

    #Debug toolbar
    'debug_toolbar.middleware.DebugToolbarMiddleware',

    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    'openearth.libs.middleware.LoginRequiredMiddleware',

    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',

    # Enable reversion globally'
    'reversion.middleware.RevisionMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
)
########## END MIDDLEWARE CONFIGURATION
CMS_PLACEHOLDER_CACHE = False
CMS_PAGE_CACHE = False
CMS_PLUGIN_CACHE = False
CMS_CACHE_DURATIONS = dict(
    content=1,
    menus=1,
    permissions=60,
    placeholder=2,
    show_placeholder=2,
    static_placeholder=2,
)
# import datetime
# CMS_CACHE_PREFIX = '%s' % datetime.datetime.now()
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
    },
}

########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = 'urls'
########## END URL CONFIGURATION


########## ALLOWED HOSTS CONFIGURATION
ALLOWED_HOSTS = ['.openearthdata.nl', '131.180.123.232', '131.180.123.184', '131.180.123.250']
########## END ALLOWED HOSTS CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.gis',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Useful template tags:
    'django.contrib.humanize',
)

THIRD_PARTY_APPS = (
    # Database migration helpers:
    'south',

    # Django extensions
    'django_extensions',

    # Redis status:
    'redis_status',

    # Websockets for redis:
    'ws4redis',

    # django-filer:
    'filer',
    'easy_thumbnails',

    # Sentry
    #'raven.contrib.django.raven_compat', # moved to test/prod settings

    # Tags input for tags in the admin
    'tags_input',

    # Django CMS stuff
    'cms',  # django CMS itself
    'mptt',  # utilities for implementing a tree
    'menus',  # helper for model independent hierarchical website navigation
    'sekizai',  # for javascript and css management
    # # for the admin skin. You **must** add 'djangocms_admin_style' in the list
    # # **before** 'django.contrib.admin'.
    'djangocms_admin_style',
    'treebeard',

    'djangocms_file',
    'djangocms_flash',
    'djangocms_googlemap',
    'djangocms_inherit',
    'djangocms_picture',
    'djangocms_teaser',
    'djangocms_video',
    'djangocms_link',
    'djangocms_snippet',
    'djangocms_text_ckeditor',

    # Version tracking
    'reversion',
)

LOCAL_APPS = (
    'system',
    'openearth',
    'openearth.apps.processing',
    'openearth.apps.script_execution_manager',
    'openearth.apps.kmlserver',
    'openearth.apps.documentation',
    'cms_extension',
)

DJANGO_POST_APPS = (
    # Admin panel and documentation:
    'django.contrib.admin',
    'django.contrib.admindocs',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + DJANGO_POST_APPS
########## END APP CONFIGURATION

TAGS_INPUT_MAPPINGS = {
    'processing.Extension': {
        'fields': ('extension', 'name'),
        'ordering': ['name', 'extension'],
        'create_missing': True,
    },
}

########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/srv/{0}/log/{0}.log'.format(SITE_NAME),
            'maxBytes': 50000,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'INFO',
        },
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        '%s' % SITE_NAME: {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'src.%s' % SITE_NAME: {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
########## END LOGGING CONFIGURATION


########## REDIS CONFIGURATION
REDIS_PASSWORD = ""

# Websocket for redis
WS4REDIS_CONNECTION = {
    'host': '127.0.0.1',
    'port': 6379,
    'db': 5,
    'password': REDIS_PASSWORD,
}
WS4REDIS_STORE = 'openearth.apps.script_execution_manager.store.RedisHistoryStore'

WEBSOCKET_URL = '/ws/'

WS4REDIS_EXPIRE = 3600

WEBSOCKETLOGGER = {
    # How many seconds after last update, will the history be purged?
    'expire_history': 3600,

}
########## END REDIS CONFIGURATION


########## CELERY CONFIGURATION
# See: http://celery.readthedocs.org/en/latest/configuration.html#celery-task-result-expires
CELERY_TASK_RESULT_EXPIRES = timedelta(minutes=30)

# See: http://docs.celeryproject.org/en/master/configuration.html#std:setting-CELERY_CHORD_PROPAGATES
CELERY_CHORD_PROPAGATES = True

BROKER_URL = "redis://:%s@127.0.0.1:6379/0" % REDIS_PASSWORD
CELERY_RESULT_BACKEND = "redis://:%s@127.0.0.1:6379/1" % REDIS_PASSWORD
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERYD_POOL_RESTARTS = True
CELERY_TRACK_STARTED = True
# 4 cores= 4 worker threads (preforked)
CELERYD_CONCURRENCY = 4
# Maximum of tasks before restarting worker. This frees memory from potential
# memory leaks.
CELERYD_MAX_TASKS_PER_CHILD = 20
########## END CELERY CONFIGURATION


########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'openearth.wsgi.application'
########## END WSGI CONFIGURATION

########## CONTAINER CONFIGURATION
CONTAINER = {
    "base_dir": os.environ.get('CONTAINER_BASE_DIR'),
    #"base_image": os.environ.get('CONTAINER_BASE_IMAGE'),
}
########## END CONTAINER CONFIGURATION

# directory where the root of the dataset is located. Adapt by provisioning with sed script.
DATASET_ROOT = '/demodata/'


########## DJANGO FILER
FILER_DEBUG = DEBUG

FILER_ENABLE_PERMISSIONS = True

# Should newly uploaded files have permission checking disabled (be public) by default.
# Defaults to False (new files have permission checking disable, are public)
FILER_IS_PUBLIC_DEFAULT = False

FILER_STORAGES = {
    'private': {
        'main': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': '%s' % abspath(join(dirname(SITE_ROOT), 'smedia/files')),
                'base_url': '/smedia/',
            },
            'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
        },
        'thumbnails': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': '%s' % abspath(join(dirname(SITE_ROOT), 'smedia/files/files_thumbnails')),
                'base_url': '/smedia/files_thumbnails/',
            },
        },
        'kml': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': '/data/kml',
                'base_url': '/kml/',
            },
        },
    },
}

FILER_SERVERS = {
    'private': {
        'main': {
            'ENGINE': 'filer.server.backends.nginx.NginxXAccelRedirectServer',
            'OPTIONS': {
                'location': FILER_STORAGES['private']['main']['OPTIONS']['location'],
                'nginx_location': '/secure_downloads',
            },
        },
        'thumbnails': {
            'ENGINE': 'filer.server.backends.nginx.NginxXAccelRedirectServer',
            'OPTIONS': {
                'location': FILER_STORAGES['private']['thumbnails']['OPTIONS']['location'],
                'nginx_location': '/secure_download_thumbnails',
            },
        },
         'kml': {
            'ENGINE': 'filer.server.backends.nginx.NginxXAccelRedirectServer',
            'OPTIONS': {
                'location': FILER_STORAGES['private']['kml']['OPTIONS']['location'],
                'nginx_location': '/secure_kml',
            },
        },
    },
}

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    #'easy_thumbnails.processors.scale_and_crop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)
########## END DJANGO FILER

########## ENVIRONMENT SVN
ENVIRONMENT_SVN_URL = os.environ.get('ENVIRONMENT_SVN_URL')
ENVIRONMENT_SVN_USERNAME = os.environ.get('ENVIRONMENT_SVN_USERNAME')
ENVIRONMENT_SVN_PASSWORD = os.environ.get('ENVIRONMENT_SVN_PASSWORD')
ENVIRONMENT_SVN_SCRIPTS = 'scripts/'
ENVIRONMENT_SVN_SETTINGS = {
    'url': ENVIRONMENT_SVN_URL,
    'username': ENVIRONMENT_SVN_USERNAME,
    'password': ENVIRONMENT_SVN_PASSWORD,
    'scripts': ENVIRONMENT_SVN_SCRIPTS,
}
########## END ENVIRONMENT SVN

########## ENVIRONMENT THREDDS
OPENDAP_DATA_DIR = os.environ.get('OPENDAP_DATA_DIR')
########## END ENVIRONMENT THREDDS

########## ENVIRONMENT KML
KML_FILE_DIR = os.environ.get('KML_FILE_DIR', '/data/kml')
KML_FILE_EXTS = ('.kml', '.kmz', '.png')
KML_NGINX_LOCATION = '/secure_kml'
########## END ENVIRONMENT KML


########## PASSWORD POLICY
# LDAP
# Er mag geen @ en geen spatie in het pw staan
# Het pw moet minstens uit 8 karakters bestaan
# Het moet een mix zijn van upper en lower letters, cijfers, speciale tekens.

PASSWORD_MIN_LENGTH = 8  # Defaults to 6
PASSWORD_MAX_LENGTH = 120  # Defaults to None
PASSWORD_DICTIONARY = None  # Defaults to None
PASSWORD_MATCH_THRESHOLD = 1.0  # Defaults to 0.9, should be 0.0 - 1.0 where 1.0 means exactly the same.
#PASSWORD_COMMON_SEQUENCES = []  # Should be a list of strings, see passwords/validators.py for default
PASSWORD_IVALID_CHARCTERS = " @"

OPEN_EARTH_TOOLS_URL = 'https://svn.oss.deltares.nl/repos/openearthtools/trunk/'
OPEN_EARTH_TOOLS_PATH = '/home/worker/oetools'
OPEN_EARTH_TOOLS_USERNAME = 'contact.x'
OPEN_EARTH_TOOLS_PASSWORD = '9a8syaewf'

OPEN_EARTH_TOOLS_PYTHON_URL = OPEN_EARTH_TOOLS_URL + 'python/'
OPEN_EARTH_TOOLS_PYTHON_PATH = os.path.join(OPEN_EARTH_TOOLS_PATH, 'python')
OPEN_EARTH_TOOLS_PYTHON_USERNAME = OPEN_EARTH_TOOLS_USERNAME
OPEN_EARTH_TOOLS_PYTHON_PASSWORD = OPEN_EARTH_TOOLS_PASSWORD

OPEN_EARTH_TOOLS_MATLAB_URL = OPEN_EARTH_TOOLS_URL + 'matlab/'
OPEN_EARTH_TOOLS_MATLAB_PATH = os.path.join(OPEN_EARTH_TOOLS_PATH, 'matlab')
OPEN_EARTH_TOOLS_MATLAB_USERNAME = OPEN_EARTH_TOOLS_USERNAME
OPEN_EARTH_TOOLS_MATLAB_PASSWORD = OPEN_EARTH_TOOLS_PASSWORD

CONTACT_ADDRESS = None  # The contact mail address

PASSWORD_COMPLEXITY = {  # You can ommit any or all of these for no limit for that particular set
    "UPPER": 1,        # Uppercase
    "LOWER": 1,        # Lowercase
    "DIGITS": 1,       # Digits
    "PUNCTUATION": 0,  # Punctuation (string.punctuation)
    "NON ASCII": 0,    # Non Ascii (ord() >= 128)
    "WORDS": 0         # Words (substrings seperates by a whitespace)
}

########## END PASSWORD POLICY
