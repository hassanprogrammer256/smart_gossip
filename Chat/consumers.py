import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import *

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = f"{self.scope['url_route']['kwargs']['group_name']}_Group"
        await self.channel_layer.group_add(self.group_name,self.channel_name)
        await self.accept()

    async def disconnect(self):
        await self.channel_layer.group_discard(self.group_name,self.channel_name)

