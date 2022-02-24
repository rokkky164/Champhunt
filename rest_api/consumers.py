import json
from channels.generic.websocket import AsyncWebsocketConsumer


class PitchPostConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "pitch_post"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        posted_pitch_data = await self.get_posted_pitch_data(text_data)

    async def get_posted_pitch_data(self, text_data):
        await self.send(text_data=json.dumps(text_data["data"]))


class PitchCommentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.pitch_id = self.scope["url_route"]["kwargs"]["pitch_id"]
        self.group_name = f"pitch_comment-{self.pitch_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        pitch_comment = await self.get_pitch_comment(text_data)

    async def get_pitch_comment(self, text_data):
        await self.send(text_data=json.dumps(text_data["data"]))


class PitchScoreConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.pitch_id = self.scope["url_route"]["kwargs"]["pitch_id"]
        self.group_name = f"pitch_score-{self.pitch_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        pitch_runs = await self.get_pitch_runs(text_data)

    async def get_pitch_runs(self, text_data):
        await self.send(text_data=json.dumps(text_data["data"]))
