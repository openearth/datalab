#from ws4redis import websocket
from django.core.handlers.wsgi import WSGIRequest

from ws4redis.store import RedisStore
from django.conf import settings
import re
import logging

logger = logging.getLogger(__name__)
re_ns = re.compile('^{0}(.*)'.format(settings.WEBSOCKET_URL), re.IGNORECASE)


class RedisHistoryStore(RedisStore):
    """
    RedisStore for ws4redis, with history and pattern-matched messages.

    Another difference is: it does not require a request object. This store does
    not support sending and subscribing to specific channels. It does support
    messages of type pmessage, and subscribes with the redis function:
    .psubscribe instead of .subscribe.
    """
    subscription_channels = ['subscribe-user', 'subscribe-superuser', 'subscribe-broadcast']
    publish_channels = ['publish-user', 'publish-broadcast']

    def subscribe_channels(self, request_or_config, channels, *args, **kwargs):
        """
        Initialize the channels used for subscribing and sending messages.

        This differs from the original RedisStore, in that there is no request
        object required. request_or_config can either be a request, or a dict
        with keys: namespace and username.

        Arguments:
            channels: a list, containing publish and subscribe channels.
                eg: ['subscribe-user', 'publish-user']
            request_or_config:
                a request object or dict containing keys:
                namespace: usually an UUID string (key in redis)
                username: string with username.
        """
        if isinstance(request_or_config, WSGIRequest):
            username = request_or_config.user.username
            match_ns = re_ns.match(request_or_config.path_info)
            namespace = match_ns.group(1)
        else:
            username = request_or_config['username']
            namespace = request_or_config['namespace']

        def subscribe_for(prefix):
            key = '{0}{1}'.format(prefix, namespace)
            logger.debug('Subscribing to key: {0}'.format(key))
            self._subscription.psubscribe(key)
            # old style subscribe
            #self._subscription.subscribe(key)

        def publish_on(prefix):
            key = '{0}{1}'.format(prefix, namespace)
            logger.debug('Publishing to key: {0}'.format(key))
            self._publishers.add(key)

        self._subscription = self._connection.pubsub()
        self._publishers = set()
        if 'subscribe-user' in channels and username:
            subscribe_for('{0}:'.format(username))
        if 'subscribe-broadcast' in channels:
            subscribe_for('_broadcast_:')
        if 'subscribe-superuser' in channels:
            subscribe_for('*:')

        if 'publish-user' in channels and username:
            publish_on('{0}:'.format(username))
        if 'publish-broadcast' in channels:
            publish_on('_broadcast_:')

    def publish_message(self, message):
        super(RedisHistoryStore, self).publish_message(message)
        for channel in self._publishers:
            self._connection.rpush('{0}:hist'.format(channel), message)
            self._connection.expire(channel, 3600)

    def get_history_key(self, pattern):
        """
        Get key which contains history
        Raises:
            Exception on multiple keys
        Returns:
            key name, or None

        """
        logger.debug('Get history key for "{0}"'.format(pattern))
        keys = self._connection.keys(pattern)
        return self._connection.keys(pattern)[0] if keys else None

    def send_persisted_messages(self, websocket, *args, **kwargs):
        """
        Sends message persisted (string), but also sends history stored (list).
        """
        super(RedisHistoryStore, self).send_persited_messages(websocket, *args, **kwargs)
        logger.info('sending persistent msgs for channels: {0}'.format(self._subscription.channels))

        # We swapped channels for patterns
        # for channel in self._subscription.channels:
        #     logger.info('sending persistent msgs: {0}'.format(channel))
        #     history = self._connection.lrange('{0}:hist'.format(channel), 1, -1)
        #     [websocket.send(msg) for msg in history if history]
        #     #logger.info([msg for msg in history if history])

        for channel in self._subscription.patterns:
            logger.info('sending persistent msgs: {0}'.format(channel))
            key = self.get_history_key('{0}:hist'.format(channel))
            history = self._connection.lrange(key, 1, -1)
            [websocket.send(msg) for msg in history if history]


    # fix typo in original code
    send_persited_messages = send_persisted_messages
