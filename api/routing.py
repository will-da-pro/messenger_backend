from django.urls import re_path

from . import consumers

# Allows websocket connections with regex, so that the channel name can be used in the url
websocket_urlpatterns = [
    re_path(r"ws/channels/(?P<channel_id>[\w-]+)/$", consumers.ChannelConsumer.as_asgi()),
]
