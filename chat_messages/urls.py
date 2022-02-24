from django.urls import path, re_path

from .views import (
    ChatMessageView,
    ChatRoomView,
)

app_name = "chat"

urlpatterns = [
    path("", ChatMessageView.as_view(), name="chat_index_view"),
    path("<str:room_id>/", ChatRoomView.as_view(), name="chat_room"),
]
