import json
from typing import cast

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.forms import model_to_dict

from .models import User, Channel, Message
from .serializers import MessageSerializer


# Websocket connection for real-time messages


class ChannelConsumer(AsyncWebsocketConsumer):
    def __init__(self):
        super().__init__()

        # Set class attributes
        self.user: User | None = None
        self.channel: Channel | None = None
        self.channel_group_name: str | None = None

    @staticmethod
    def clean_json(raw_json: dict) -> dict:
        # Convert data to JSON types
        for key, value in raw_json.items():
            if value is None:
                continue

            if isinstance(value, bool):
                continue

            if isinstance(value, (int, float)):
                continue

            raw_json[key] = str(value)

        return raw_json

    async def message_from_id(self, message_id: str) -> Message | None:
        if self.user is None or self.channel is None:
            return None

        is_author = await sync_to_async(self.channel.messages.filter(pk=message_id, author=self.user).exists)()

        if not is_author:
            return None

        message: Message | None = await sync_to_async(self.channel.messages.filter(pk=message_id).first)()

        return message

    async def handle_send_message(self, text_data_json: dict) -> None:
        message: dict | None = text_data_json.get("message")

        if message is None:
            return

        if self.user is None or self.channel is None or self.channel_group_name is None:
            return

        clean_message: dict = {"content": message["content"], "reply_to": message["reply_to"], "author": self.user.id,
                               "channel": self.channel.id}

        # Ensure that the message contains valid data in the correct format, and turn that into a python object
        serializer = MessageSerializer(data=clean_message)

        valid = await sync_to_async(serializer.is_valid)()

        if valid:
            # Save the message to the database
            await sync_to_async(serializer.save)()

            message_data = serializer.data

            message_data = self.clean_json(message_data)

            # Send the message to all the members of the same group
            await self.channel_layer.group_send(
                self.channel_group_name, {"type": "channel.message", "message": message_data}
            )

    async def handle_edit_message(self, text_data_json):
        message_edit: dict | None = text_data_json.get("message")

        if message_edit is None:
            return

        message_id = message_edit.get("id")
        message_content = message_edit.get("content")

        if message_id is None or message_content is None:
            return

        message = await self.message_from_id(str(message_id))

        if message is None:
            return

        message.content = str(message_content)
        message.edited = True
        await sync_to_async(message.save)()

        if self.channel_group_name is None:
            return

        message_data = model_to_dict(message)
        message_data["id"] = message_id
        message_data["created_at"] = message.created_at

        message_data = self.clean_json(message_data)

        # Send the message to all the members of the same group
        await self.channel_layer.group_send(
            self.channel_group_name, {"type": "channel.edit", "message": message_data}
        )

    async def handle_delete_message(self, text_data_json):
        message_id = text_data_json.get("id")

        if message_id is None:
            return

        message = await self.message_from_id(str(message_id))

        if message is None:
            return

        await sync_to_async(message.delete)()

        if self.channel_group_name is None:
            return

        # Send the message to all the members of the same group
        await self.channel_layer.group_send(
            self.channel_group_name, {"type": "channel.delete", "message": str(message_id)}
        )

    async def connect(self):
        # Get user and make sure they are authenticated
        self.user = cast(User | None, self.scope["user"])

        if self.user is None:
            await self.close()
            return

        if not self.user.is_authenticated:
            await self.close()
            return

        # Get the current channel
        channel_id: str = self.scope["url_route"]["kwargs"]["channel_id"]

        try:
            self.channel = await sync_to_async(Channel.objects.get)(id=channel_id)

        except Channel.DoesNotExist:
            await self.close()
            return

        if self.channel is None:
            await self.close()
            return

        # Ensure the user is actually a member of the channel they are trying to connect to
        # Prevents malicious users from accessing data they shouldn't
        is_member = await sync_to_async(self.channel.members.filter(pk=self.user.pk).exists)()

        if not is_member:
            await self.close()
            return

        # When a new message is sent, it will be sent to all connections with the same group name
        self.channel_group_name: str = f"channel_{self.channel.id}"

        if self.channel_group_name is None:
            await self.close()
            return

        await self.channel_layer.group_add(self.channel_group_name, self.channel_name)

        # If everything is ok, accept the connection
        await self.accept()

    async def disconnect(self, close_code):
        if self.channel_group_name is None:
            return

        await self.channel_layer.group_discard(self.channel_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None) -> None:
        if text_data is None:
            return

        # Get the message data
        text_data_json = json.loads(text_data)

        if self.user is None or self.channel is None:
            await self.close()
            return

        message_type = text_data_json.get("type")

        if message_type is None:
            return

        if message_type == "message":
            await self.handle_send_message(text_data_json)

        elif message_type == "edit":
            await self.handle_edit_message(text_data_json)

        elif message_type == "delete":
            await self.handle_delete_message(text_data_json)

    # Sends the message to all the clients over serial
    async def channel_message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({'type': 'message', 'message': message}))

    async def channel_edit(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({'type': 'edit', 'message': message}))

    async def channel_delete(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({'type': 'delete', 'id': message}))
