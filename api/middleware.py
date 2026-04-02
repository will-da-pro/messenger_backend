from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from .models import User


# Custom middleware for token authentication with websockets
# Preferred over session authentication because it works better when using an api
# rather than connecting to the server directly.


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Ensure the connection is actually from a websocket
        if scope['type'] == 'websocket':
            query_string = scope.get('query_string', b'').decode()
            token = None

            # Get the token from the url
            for param in query_string.split('&'):
                if param.startswith('token='):
                    token = param.split('=')[1]
                    break

            # Get the user's model from their token
            if token:
                scope['user'] = await self.get_user_from_token(token)
            else:
                scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token):
        # Check if the token sent by the incoming connection is valid,
        # and returns the associated user
        try:
            user_id = Token.objects.get(key=token).user_id
            user = User.objects.get(pk=user_id) 
            return user
        except User.DoesNotExist:
            return AnonymousUser()
