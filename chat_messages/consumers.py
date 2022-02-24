import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from accounts.models import User

from .models import ChatRoom, ChatMessage, Thread


class ChatRoomConsumer(WebsocketConsumer):
    def fetch_messages(self, data):
        messages = self._get_last_20_messages(data["room_id"])
        content = {"command": "messages", "messages": self.messages_to_json(messages)}
        self.send_message(content)

    @staticmethod
    def _get_last_20_messages(room_id):
        return ChatRoom.objects.get(room_id=room_id).messages.all().order_by("-id")[:20]

    def new_message(self, data):
        """
        data = {
                "command": "new_message",
                "message": "Hello Everyone!",
                "from_username": "rokkky",
                "room_id": 121
            }
        """
        user = User.objects.get(username=data["from_username"])
        message = ChatMessage.objects.create(user=user, message=data["message"])
        current_chat = ChatRoom.objects.get(room_id=data["room_id"])
        current_chat.messages.add(message)
        current_chat.save()
        content = {"command": "new_message", "message": self.message_to_json(message)}
        return self.send_chat_message(content)

    def messages_to_json(self, messages):
        result = []
        for message in messages:
            result.append(self.message_to_json(message))
        return result

    def message_to_json(self, message):
        return {
            "id": message.id,
            "author": message.user.username,
            "content": message.message,
            "timestamp": str(message.timestamp),
        }

    commands = {"fetch_messages": fetch_messages, "new_message": new_message}

    def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = "chat_%s" % self.room_id
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        self.commands[data["command"]](self, data)

    def send_chat_message(self, message):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": "chat_message", "message": message}
        )

    def send_message(self, message):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": "fetch_previous_message", "message": message}
        )

    def chat_message(self, event):
        message = event["message"]
        self.send(text_data=json.dumps(message))

    def fetch_previous_message(self, event):
        message = event["message"]
        self.send(text_data=json.dumps(message))


class OneToOneChatConsumer(WebsocketConsumer):
    def messages_to_json(self, messages):
        result = []
        for message in messages:
            result.append(self.message_to_json(message))
        return result

    def message_to_json(self, message):
        return {
            "id": message.id,
            "author": message.user.username,
            "content": message.message,
            "timestamp": str(message.timestamp),
        }

    def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            self.onetoonechat_group_name = "random_grp"
            self.close()
        else:
            user_id = self.scope["user"]
            self.other_user_id = self.scope["url_route"]["kwargs"]["user_id"]
            other_user = User.objects.get(id=self.other_user_id)
            user = User.objects.get(id=user_id)
            thread_obj = Thread.objects.get_or_create_personal_thread(user, other_user)
            self.onetoonechat_group_name = f"personal_thread_{thread_obj.id}"

            async_to_sync(self.channel_layer.group_add)(
                self.onetoonechat_group_name, self.channel_name
            )
            self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.onetoonechat_group_name, self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)


"""
import websocket
ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:8001/ws/messages/12111/")
"""
