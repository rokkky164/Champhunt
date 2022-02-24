import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.user_group_name = "notification_%s" % self.user_id
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def send_notification(self, event):
        message = json.loads(event["value"])
        await self.send(text_data=json.dumps(message))

    async def receive(self, text_data):
        await self.send_notification(text_data)
