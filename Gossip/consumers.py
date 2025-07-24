from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
from stream_chat import StreamChat
from django.conf import settings
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       self.stream_client = StreamChat(
           api_key=settings.STREAM_API_KEY,
           api_secret=settings.STREAM_API_SECRET
       )
       self.user_id = None
       self.username = None
       self.channel = None
       self.group_name = None
       self.group_group_name = None
       self.channel_layer = get_channel_layer()

    async def connect(self):
        try:
            self.group_name = self.scope['url_route']['kwargs']['group_name']
            self.group_group_name = f'chat_{self.group_name}'

            # Generate a unique user ID for anonymous users
            self.user_id = self.scope["user"].id if self.scope.get("user", None) and self.scope["user"].is_authenticated else f"anon_{id(self)}"
            self.username = f"Anonymous_{self.user_id}"

            # Create or update the user in Stream
            await sync_to_async(self.stream_client.upsert_user)({
                "id": str(self.user_id),
                "role": "user",
                "name": self.username
            })

            # Generate Stream token
            token = await sync_to_async(self.stream_client.create_token)(str(self.user_id))

            # Add to channel layer group
            await self.channel_layer.group_add(
                self.group_group_name,
                self.channel_name
            )

            # Accept the WebSocket connection
            await self.accept()

            # Send initial connection data
            await self.send(text_data=json.dumps({
                "type": "connection_established",
                "token": token,
                "user_id": str(self.user_id),
                "username": self.username
            }))

            logger.info(f"WebSocket connected for user {self.user_id} in group {self.group_name}")

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
       try:
           if self.group_group_name:
               await self.channel_layer.group_discard(
                   self.group_group_name,
                   self.channel_name
               )
           logger.info(f"WebSocket disconnected for user {self.user_id} with code {close_code}")
       except Exception as e:
           logger.error(f"Error in disconnect: {str(e)}", exc_info=True)

    async def receive(self, text_data):
       try:
           data = json.loads(text_data)
           message_type = data.get("type")
           logger.debug(f"Received message of type {message_type} from user {self.user_id}")

           if message_type == "set_username":
               await self.handle_set_username(data)
           elif message_type == "create_channel":
               await self.handle_create_channel()
           elif message_type == "send_message":
               await self.handle_send_message(data)
           else:
               logger.warning(f"Unknown message type received: {message_type}")

       except json.JSONDecodeError as e:
           logger.error(f"JSON decode error: {str(e)}")
           await self.send_error("Invalid message format")
       except Exception as e:
           logger.error(f"Error in receive: {str(e)}", exc_info=True)
           await self.send_error(str(e))

    async def handle_set_username(self, data):
       try:
           self.username = data.get("username")
           self.user_id = self.username  # Update user_id to match username

           # Update user in Stream
           await sync_to_async(self.stream_client.upsert_user)({
               "id": str(self.user_id),
               "role": "user",
               "name": self.username
           })

           # Generate new token
           token = await sync_to_async(self.stream_client.create_token)(str(self.user_id))

           await self.send(text_data=json.dumps({
               "type": "username_set",
               "username": self.username,
               "token": token
           }))

           logger.info(f"Username set to {self.username} for user {self.user_id}")

       except Exception as e:
           logger.error(f"Error setting username: {str(e)}", exc_info=True)
           await self.send_error("Failed to set username")

    async def handle_create_channel(self):
       try:
           # Initialize Stream channel
           self.channel = self.stream_client.channel("messaging", self.group_name)

           # Create the channel with minimal data first
           await sync_to_async(self.channel.create)(str(self.user_id))

           # Add members after creation
           await sync_to_async(self.channel.add_members)([str(self.user_id)])

           # Query channel history
           response = await sync_to_async(self.channel.query)(
               state=True,
               messages={"limit": 50}
           )

           # Send historical messages
           for message in response["messages"]:
               await self.send(text_data=json.dumps({
                   "type": "message_received",
                   "message": message
               }))

           # Confirm channel creation
           await self.send(text_data=json.dumps({
               "type": "channel_created",
               "channel_id": self.group_name
           }))

           logger.info(f"Channel {self.group_name} created successfully")

       except Exception as e:
           logger.error(f"Error creating channel: {str(e)}", exc_info=True)
           await self.send_error("Failed to create channel")

    async def handle_send_message(self, data):
       try:
           if not self.channel:
               self.channel = self.stream_client.channel("messaging", self.group_name)

           message = {
               "text": data.get("message"),
               "user": {
                   "id": str(self.user_id),
                   "name": self.username
               },
               "is_local": True  # Add a flag to identify local messages
           }

           response = await sync_to_async(self.channel.send_message)(
               message,
               str(self.user_id)
           )

           logger.info(f"Message sent by {self.username} in channel {self.group_name}")

       except Exception as e:
           logger.error(f"Error sending message: {str(e)}", exc_info=True)
           await self.send_error("Failed to send message")

    async def chat_message(self, event):
       try:
           message = event['message']
           await self.send(text_data=json.dumps({
               'type': 'message_received',
               'message': message
           }))
           logger.debug(f"Broadcasted message in group {self.group_name}")
       except Exception as e:
           logger.error(f"Error in chat_message: {str(e)}", exc_info=True)

    async def send_error(self, message):
       await self.send(text_data=json.dumps({
           "type": "error",
           "message": message
       }))

