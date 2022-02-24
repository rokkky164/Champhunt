import channels

from django.shortcuts import render
from django.views.generic import View, TemplateView

from asgiref.sync import async_to_sync

from WallStreet.mixins import LoginRequiredMixin


class ChatMessageView(LoginRequiredMixin, TemplateView):
    template_name = "chat_messages/chat_index.html"


class ChatRoomView(LoginRequiredMixin, TemplateView):
    template_name = "chat_messages/chatroom.html"

    def get(self, request, room_id, *args, **kwargs):
        return self.render_to_response(
            {"room_id": room_id, "username": request.user.username}
        )
