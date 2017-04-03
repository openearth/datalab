from django.contrib.auth.models import User
from django.test import TestCase
import logging
from mock import MagicMock
import redis
from ws4redis import settings as redis_settings
import socket
from ..logger import WebsocketLoggerHandler


class WebsocketLoggerHandlerTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._redis_connection = redis.StrictRedis(**redis_settings.WS4REDIS_CONNECTION)
        cls.namespace = '426db016-dc2d-45a4-9b95-f11a3ddedc3f'
        # Create a mocked websocket; which does nothing.
        cls.sock = MagicMock(name='socket', spec=socket.socket)

    def setUp(self):
        # Every test needs access to the request factory.
        self.user = User.objects.create_user(
            username='admin', email='test@test.com', password='top_secret'
        )
        # Clean up the keys.
        self._redis_connection.delete('{0}:{1}'.format(
            self.user.username, self.namespace
        ))
        self._redis_connection.delete('{0}:{1}:hist'.format(
            self.user.username, self.namespace
        ))

    def test_log_debug(self):
        config = {
            'username': self.user.username,
            'namespace': self.namespace
        }
        logger = logging.getLogger(__name__)

        redis_handler = WebsocketLoggerHandler(config=config, channels=['subscribe-user', 'publish-user'])
        logger.addHandler(redis_handler)
        message = 'test test test'
        logger.debug(message)
        history = self._redis_connection.lrange('admin:426db016-dc2d-45a4-9b95-f11a3ddedc3f:hist', 0, -1)
        #print history[0]
        self.assertEqual(
            history[0],
            message
        )


    def test_log_debug_format(self):
        """
        Tests if formatter is respected.
        """
        config = {
            'username': self.user.username,
            'namespace': self.namespace
        }
        logger = logging.getLogger(__name__)

        redis_handler = WebsocketLoggerHandler(config=config, channels=['subscribe-user', 'publish-user'])
        # redis_handler = logging.StreamHandler()
        template = 'Format: %(message)s'
        formatter = logging.Formatter(
            #fmt="[%(levelname)s] %(asctime)s : %(message)s",
            #fmt="[%(levelname)s] %(asctime)s : %(message)s",
            template
        )
        redis_handler.setFormatter(formatter)
        logger.addHandler(redis_handler)
        message = 'format format format'
        logger.debug(message)
        history = self._redis_connection.lrange('admin:426db016-dc2d-45a4-9b95-f11a3ddedc3f:hist', 0, -1)
        print history[0]
        self.assertEqual(
             history[0],
             template % {'message': message}
        )