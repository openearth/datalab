"""Production settings and globals."""
from base import *

########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)
########## END SECRET CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
#EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
#EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = os.environ.get('EMAIL_PORT', 25)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', False)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
#SERVER_EMAIL = EMAIL_HOST_USER
########## END EMAIL CONFIGURATION

# When using unix domain sockets
# Note: ``LOCATION`` needs to be the same as the ``unixsocket`` setting
# in your redis.conf
CACHES = {
    "default": {
        "BACKEND": "redis_cache.RedisCache",
        "LOCATION": "/var/run/redis/redis.sock",
        "OPTIONS": {
            "DB": 15,
            "PASSWORD": REDIS_PASSWORD,
            "PARSER_CLASS": "redis.connection.HiredisParser",
        },
    },
}

ALLOWED_HOSTS = [
]

# For production and acceptation add sentry/raven to the mix
INSTALLED_APPS += ('raven.contrib.django.raven_compat',)

########## SENTRY
RAVEN_CONFIG = {
    'dsn': os.environ.get('SENTRY_DSN', '') + '?verify_ssl=0&timeout=5'
}
########## END SENTRY

########## UPDATING LOGGING CONFIGURATION
LOGGING.update(
    {
        'root': {
            'level': 'ERROR',
            'handlers': ['console', 'sentry'],
        },
    }
)


LOGGING['handlers'].update(
    {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
    }
)

LOGGING['loggers']['django'] = {
    'handlers': ['console', 'sentry'],
    'propagate': True,
    'level': 'ERROR',
}

LOGGING['loggers'][SITE_NAME] = {
    'handlers': ['console', 'sentry'],
    'propagate': True,
    'level': 'ERROR',
}

LOGGING['loggers']['src.%s' % SITE_NAME] = {
    'handlers': ['console', 'sentry'],
    'propagate': True,
    'level': 'ERROR',
}

LOGGING['loggers'].update(
    {
        'django.request': {
            'level': 'ERROR',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'sentry'],
            'level': 'ERROR',
            'propagate': False,
        },
        'raven': {
            'level': 'ERROR',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'ERROR',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
    }
)
########## END LOGGING CONFIGURATION
