import json

from decimal import Decimal

from channels.generic.websocket import AsyncWebsocketConsumer

from djangochannelsrestframework import permissions
from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.mixins import CreateModelMixin, ListModelMixin
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin

from market.models import CompanyCMPRecord, Company

from .serializers import CompanyCMPRecordSerializer, CompanySerializer


class CompanyConsumer(CreateModelMixin, GenericAsyncAPIConsumer):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = (permissions.AllowAny,)


class CMPConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
    queryset = CompanyCMPRecord.objects.all()
    serializer_class = CompanyCMPRecordSerializer


class CMPRecordConsumer(GenericAsyncAPIConsumer):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = (permissions.AllowAny,)

    @model_observer(CompanyCMPRecord)
    async def companycmprecord_activity(self, message, observer=None, **kwargs):
        await self.send_json(message)

    @companycmprecord_activity.serializer
    def companycmprecord_activity(self, instance: CompanyCMPRecord, action, **kwargs):
        return CompanyCMPRecordSerializer(instance).data

    @action()
    async def subscribe_to_companycmprecord_activity(self, **kwargs):
        await self.companycmprecord_activity.subscribe()


class RealTimeCMP(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "cmp_data"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        new_cmp_record = await self.get_cmp(text_data)

    async def get_cmp(self, text_data):
        await self.send(text_data=json.dumps(text_data["data"]))
