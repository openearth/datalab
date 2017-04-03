import redis
import logging
from openearth.apps.script_execution_manager.store import RedisHistoryStore
from ws4redis import settings as redis_settings
from django.conf import settings


class WebsocketLoggerHandler(logging.Handler):
    """
    Logger Handler which writes logs to websocket, through redis.
    """
    def __init__(self, config, channels):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        #self.formatter = logging.Formatter('Format: %(message)s')
        self._redis_connection = redis.StrictRedis(
            **redis_settings.WS4REDIS_CONNECTION
        )
        self.redis_store = RedisHistoryStore(
            self._redis_connection,
            expire=settings.WEBSOCKETLOGGER['expire_history']
        )
        self.redis_store.subscribe_channels(
            request_or_config=config,
            channels=channels
        )

    def emit(self, record):
        """
        Publish message to pubsub channel and append to history.
        """
        msg = self.format(record)
        self.redis_store.publish_message(msg)