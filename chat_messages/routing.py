from django.urls import re_path

from .consumers import ChatRoomConsumer, OneToOneChatConsumer


chatsocket_urlpatterns = [
    # room chat
    re_path(r"^ws/chat/(?P<room_id>[^/]+)/$", ChatRoomConsumer.as_asgi()),
    # personal chat
    re_path(r"^ws/messages/(?P<user_id>[^/]+)/$", OneToOneChatConsumer.as_asgi()),
]
