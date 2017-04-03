import sys
from django.core.handlers.wsgi import WSGIRequest, logger, STATUS_CODE_TEXT
from django.http import HttpResponse, HttpResponseServerError, HttpResponseBadRequest
from django.utils.encoding import force_str
from ws4redis.exceptions import WebSocketError, HandshakeError, UpgradeRequiredError
from django.db import connections

def patched_call(self, environ, start_response):
    """
    Hijack main loop from original thread. Listen to Redis and Websocket events.

    This is a patch for the __call__ method inws4redis.wsgi_server-
    .WebsocketWSGIServer. This patch has support for pattern matched subscribe.
    """
    connections['default'].allow_thread_sharing = True
    websocket = None
    redis_store = self.RedisStore(self._redis_connection)
    try:
        self.assure_protocol_requirements(environ)
        request = WSGIRequest(environ)
        self.process_request(request)
        channels = self.process_subscriptions(request)
        websocket = self.upgrade_websocket(environ, start_response)
        logger.debug('Subscribed to channels: {0}'.format(', '.join(channels)))
        redis_store.subscribe_channels(request, channels)
        websocket_fd = websocket.get_file_descriptor()
        listening_fds = [websocket_fd]
        redis_fd = redis_store.get_file_descriptor()
        if redis_fd:
            listening_fds.append(redis_fd)
        redis_store.send_persited_messages(websocket)
        while websocket and not websocket.closed:
            ready = self.select(listening_fds, [], [], 4.0)[0]
            if not ready:
                # flush empty socket
                websocket.flush()
            for fd in ready:
                if fd == websocket_fd:
                    message = websocket.receive()
                    redis_store.publish_message(message)
                elif fd == redis_fd:
                    response = redis_store.parse_response()
                    if response[0] == 'message':
                        message = response[2]
                        websocket.send(message)
                    elif response[0] == 'pmessage':
                        # This is the patch. Listen to pmessage types as well.
                        # this is required for pattern subscribe.
                        message = response[3]
                        websocket.send(message)
                else:
                    logger.error('Invalid file descriptor: {0}'.format(fd))
    except WebSocketError, excpt:
        logger.warning('WebSocketError: ', exc_info=sys.exc_info())
        response = HttpResponse(status=1001, content='Websocket Closed')
    except UpgradeRequiredError, excpt:
        logger.info('Websocket upgrade required')
        response = HttpResponseBadRequest(status=426, content=excpt)
    except HandshakeError, excpt:
        logger.warning('HandshakeError: ', exc_info=sys.exc_info())
        response = HttpResponseBadRequest(content=excpt)
    except Exception, excpt:
        logger.error('Other Exception: ', exc_info=sys.exc_info())
        response = HttpResponseServerError(content=excpt)
    else:
        response = HttpResponse()
    if websocket:
        websocket.close(code=1001, message='Websocket Closed')
    if hasattr(start_response, 'im_self') and not start_response.im_self.headers_sent:
        status_text = STATUS_CODE_TEXT.get(response.status_code, 'UNKNOWN STATUS CODE')
        status = '{0} {1}'.format(response.status_code, status_text)
        start_response(force_str(status), response._headers.values())
    return response