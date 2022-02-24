from django.urls import re_path

from .consumers import UserConsumer


accountsocket_urlpatterns = [
    re_path(r"^ws/user/(?P<user_id>[^/]+)/$", UserConsumer.as_asgi()),
]
