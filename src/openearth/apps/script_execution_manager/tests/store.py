from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
import logging
from mock import MagicMock
import multiprocessing
import redis
import socket
import time
from ..store import RedisHistoryStore
from ws4redis import settings as redis_settings
from openearth.apps.processing.tests.factories import AdminFactory, \
    StaffUserFactory

logger = logging.getLogger(__name__)


class HistoryStoreTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._redis_connection = redis.StrictRedis(**redis_settings.WS4REDIS_CONNECTION)
        cls.namespace = 'c8866fe7-2a63-4596-a857-a616f3db2044'
        # Create a mocked websocket; which does nothing.
        cls.sock = MagicMock(name='socket', spec=socket.socket)

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
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

    def tearDown(self):
        super(HistoryStoreTest, self).tearDown()
        keys = self._redis_connection.keys('*hist')
        for k in keys:
            self._redis_connection.delete(k)

    def threads_base(self, messages, redis_store_user_send, redis_store_user_check):
        """
        contains threads to send messages and receive messages.
        """

        def publish_messages(messages):
            """
            Write to file after 2 seconds in seperate thread.
            """
            # store_user_1 = get_redis_store(
            #     username=user_1.username,
            #     namespace=self.namespace,
            #     #channels=['subscribe-user', 'publish-user'],
            #     channels=['publish-user']
            #
            # )
            logger.info('Write messages.')
            time.sleep(2)
            redis_store_user_send.publish_message(messages[0])
            redis_store_user_send.publish_message(messages[1])
            logger.info('Done')

        p = multiprocessing.Process(
            target=publish_messages, args=(messages,)
        )
        p.start()

        def fetch_message(msgs):
            """
            Try to get the expected messages. Will be killed within 3 seconds.
            If killed: test fails.

            This thread has to be killed; in case the unittest is wrong the
            thread might run forever.
            """
            for m in redis_store_user_check._subscription.listen():
                if m['type'] == 'pmessage':
                    print m['data']  # message 1
                    if m['data'] in msgs:
                        print 'remove: {0}'.format(m['data'])
                        msgs.remove(m['data'])
                if not msgs:
                    break

        manager = multiprocessing.Manager()
        shared = manager.list(messages)

        fm = multiprocessing.Process(
            target=fetch_message, args=(shared,)
        )
        fm.start()
        # Join thread for 10 seconds, then terminate.
        fm.join(timeout=10)
        fm.terminate()
        return shared[:]

    def get_redis_store(self, username, namespace, channels):
        """
        Return a RedisHistoryStore object for user.
        """
        redis_connection = redis.StrictRedis(**redis_settings.WS4REDIS_CONNECTION)
        redis_store = RedisHistoryStore(redis_connection)
        config = {
            'namespace': namespace,
            'username': username
        }
        redis_store.subscribe_channels(request_or_config=config, channels=channels)
        redis_store.send_persisted_messages(self.sock)
        return redis_store

    ############################################################################
    #
    # End of utility methods.
    # Write tests below.
    #
    ############################################################################

    def test_publish_message(self):
        """
        tests if message is published, stored as string and in list.
        """
        channels = ['subscribe-user', 'publish-user']
        redis_store = RedisHistoryStore(self._redis_connection)
        messages = [
            'test message 1',
            'test message 2'
        ]
        config = {
            'username': self.user.username,
            'namespace': self.namespace
        }
        redis_store.subscribe_channels(request_or_config=config, channels=channels)
        redis_store.send_persisted_messages(self.sock)
        redis_store.publish_message(messages[0])
        redis_store.publish_message(messages[1])

        name = '{0}:{1}'.format(self.user.username, self.namespace)
        self.assertEqual(
            self._redis_connection.get(name),
            'test message 2'
        )
        history = self._redis_connection.lrange('{0}:hist'.format(name), 0, -1)
        logger.debug(history)
        self.assertEqual(
            history[-2],
            messages[0]
        )
        self.assertEqual(
            history[-1],
            messages[1]
        )

    def test_publish_message_with_request_object(self):
        """
        tests if message is published, stored as string and in list.
        """
        request = self.factory.get(path='/ws/{0}'.format(self.namespace), data={})
        request.user = self.user
        redis_store = RedisHistoryStore(self._redis_connection)
        channels = ['subscribe-user', 'publish-user']
        messages = [
            'test message 1',
            'test message 2'
        ]
        redis_store.subscribe_channels(request_or_config=request, channels=channels)
        redis_store.send_persisted_messages(self.sock)
        redis_store.publish_message(messages[0])
        redis_store.publish_message(messages[1])

        name = '{0}:{1}'.format(request.user.username, self.namespace)
        self.assertEqual(
            self._redis_connection.get(name),
            'test message 2'
        )
        history = self._redis_connection.lrange('{0}:hist'.format(name), 0, -1)
        logger.debug(history)
        self.assertEqual(
            history[-2],
            messages[0]
        )
        self.assertEqual(
            history[-1],
            messages[1]
        )

    def test_superuser_reads_other_user(self):
        """
        Test if a superuser, can subscribe and read all channels.

        TODO: write check if user really is superuser? (=> not in store.py, probably in view/websocket?)
        """

        superuser = AdminFactory()
        user_1 = StaffUserFactory()
        user_2 = StaffUserFactory()
        redis_store_superuser = self.get_redis_store(
            username='.*',  # superuser requires .* as username
            namespace=self.namespace,
            channels=['subscribe-superuser']
        )
        store_user_1 = self.get_redis_store(
            username=user_1.username,
            namespace=self.namespace,
            #channels=['subscribe-user', 'publish-user'],
            channels=['publish-user']

        )
        messages = [
            'test message 1',
            'test message 2'
        ]
        # Messages should be empty
        shared = self.threads_base(
            messages=messages,
            redis_store_user_send=store_user_1,
            redis_store_user_check=redis_store_superuser
        )
        self.assertListEqual(shared[:], [])

    def test_user_1_reads_user_1(self):
        """
        Test if normal user1 can read it self.

        TODO: write check if user really is superuser? (=> not in store.py, probably in view/websocket?)
        """

        superuser = AdminFactory()
        user_1 = StaffUserFactory()
        user_2 = StaffUserFactory()
        store_user_1_conn_1 = self.get_redis_store(
            username=user_1.username,
            namespace=self.namespace,
            #channels=['subscribe-user', 'publish-user'],
            channels=['publish-user', 'subscribe-user']
        )
        store_user_1_conn_2 = self.get_redis_store(
            username=user_1.username,
            namespace=self.namespace,
            #channels=['subscribe-user', 'publish-user'],
            channels=['publish-user', 'subscribe-user']
        )
        messages = [
            'test message 1',
            'test message 2'
        ]
        # Messages should be empty
        shared = self.threads_base(
            messages=messages,
            redis_store_user_send=store_user_1_conn_1,
            redis_store_user_check=store_user_1_conn_2
        )
        self.assertListEqual(shared[:], [])

    def test_user_1_cannot_read_user_2(self):
        """
        Test if normal user1 cannot read user 2.

        TODO: write check if user really is superuser? (=> not in store.py, probably in view/websocket?)
        """
        superuser = AdminFactory()
        user_1 = StaffUserFactory()
        user_2 = StaffUserFactory()
        store_user_1_conn_1 = self.get_redis_store(
            username=user_1.username,
            namespace=self.namespace,
            #channels=['subscribe-user', 'publish-user'],
            channels=['publish-user', 'subscribe-user']
        )
        store_user_2_conn_2 = self.get_redis_store(
            username=user_2.username,
            namespace=self.namespace,
            #channels=['subscribe-user', 'publish-user'],
            channels=['publish-user', 'subscribe-user']
        )
        messages = [
            'test message 1',
            'test message 2'
        ]
        # Messages should be empty
        shared = self.threads_base(
            messages=messages,
            redis_store_user_send=store_user_1_conn_1,
            redis_store_user_check=store_user_2_conn_2
        )
        self.assertListEqual(shared[:], messages)

    def test_get_history_key(self):
        channels = ['subscribe-user', 'publish-user']
        redis_store = RedisHistoryStore(self._redis_connection)
        messages = [
            'test message 1',
            'test message 2'
        ]
        config = {
            'username': self.user.username,
            'namespace': self.namespace
        }
        redis_store.subscribe_channels(request_or_config=config, channels=channels)
        redis_store.send_persisted_messages(self.sock)
        redis_store.publish_message(messages[0])
        redis_store.publish_message(messages[1])
        pattern = '*:{0}:hist'.format(self.namespace)
        self.assertEqual(
            redis_store.get_history_key(pattern=pattern),
            '{0}:{1}:hist'.format(self.user.username, self.namespace)
        )



    def test_get_history_key_returns_none_if_not_exist(self):
        channels = ['subscribe-user', 'publish-user']
        redis_store = RedisHistoryStore(self._redis_connection)
        messages = [
            'test message 1',
            'test message 2'
        ]
        config = {
            'username': self.user.username,
            'namespace': self.namespace
        }
        redis_store.subscribe_channels(request_or_config=config, channels=channels)
        redis_store.send_persisted_messages(self.sock)
        redis_store.publish_message(messages[0])
        redis_store.publish_message(messages[1])
        self.assertIsNone(redis_store.get_history_key(pattern='*:doesntexist:hist'.format(self.namespace)))
