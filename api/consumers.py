import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import User, Channel
from .serializers import MessageSerializer


# Websocket connection for real-time messages


class ChannelConsumer(AsyncWebsocketConsumer):
    def __init__(self):
        super().__init__()

        # Set class attributes
        self.user: User | None = None
        self.channel: Channel | None = None
        self.channel_group_name: str | None = None

    async def connect(self):
        # Get user and make sure they are authenticated
        self.user = self.scope["user"]

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
        await self.channel_layer.group_add(self.channel_group_name, self.channel_name)

        # If everything is ok, accept the connection
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.channel_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None) -> None:
        # Get the message data
        text_data_json = json.loads(text_data)

        if self.user is None or self.channel is None:
            await self.close()
            return

        text_data_json["author"] = self.user.id
        text_data_json["channel"] = self.channel.id

        # Ensure that the message contains valid data in the correct format, and turn that into a python object
        serializer = MessageSerializer(data=text_data_json)

        valid = await sync_to_async(serializer.is_valid)()

        if valid:
            # Save the message to the database
            await sync_to_async(serializer.save)()

            # Convert the message back into a format which can be sent over websocket
            message = {
                "id": str(serializer.data["id"]),
                "content": serializer.data["content"],
                "created_at": serializer.data["created_at"],
                "author": str(serializer.data["author"]),
                "channel": str(serializer.data["channel"]),
                "reply_to": str(serializer.data["reply_to"]) if serializer.data["reply_to"] is not None else None,
            }

            # Send the message to all the members of the same group
            await self.channel_layer.group_send(
                self.channel_group_name, {"type": "channel.message", "message": message}
            )

    # Sends the message to all the clients over serial
    async def channel_message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))
