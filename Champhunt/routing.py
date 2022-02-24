from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from real_time_cmp import consumers

from accounts.routing import accountsocket_urlpatterns
from chat_messages.routing import chatsocket_urlpatterns
from push_notifications.routing import push_notifications_urlpatterns
from rest_api.routing import rest_api_urlpatterns

from .middleware import TokenAuthMiddleware

ws_pattern = [
    path("ws/realtime-cmp/", consumers.RealTimeCMP.as_asgi()),
]

ws_pattern += accountsocket_urlpatterns
ws_pattern += chatsocket_urlpatterns
ws_pattern += push_notifications_urlpatterns
ws_pattern += rest_api_urlpatterns

application = ProtocolTypeRouter(
    {"websocket": AuthMiddlewareStack(URLRouter(ws_pattern))}
)
