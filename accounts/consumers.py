import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from .models import User


class UserConsumer(WebsocketConsumer):
    def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.user_group_name = f"user_{self.user_id}"
        async_to_sync(self.channel_layer.group_add)(
            self.user_group_name, self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.user_group_name, self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        self.commands[data["command"]](self, data)

    def update_user_cash_on_topnavbar(self, text_data):
        self.send(text_data=json.dumps(text_data["data"]))
