from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, views, viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .serializers import (
    UserSerializer,
    MessageSerializer,
    ChannelSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    LeaveChannelSerializer,
)
from .models import User, Message, Channel
from .permissions import IsUserOrReadOnly, IsOwnerOrReadOnly


# Create your views here.


# Rest framework api endpoint for user creation
class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# Rest framework api endpoint for user login
class UserLoginView(views.APIView):
    @staticmethod
    def post(request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]
            # Authenticate the user
            user = authenticate(username=username, password=password)

            if user:
                token, created = Token.objects.get_or_create(user=user)
                return Response(
                    {
                        "token": token.key,
                        "user_id": str(user.id),
                    }
                )

            else:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Rest framework api endpoint for changing user password
class UserChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        # user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Password changed successfully."}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Rest framework api endpoint for viewing all users
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "channels",
        "owned_channels",
    ]
    # Allows anyone to read all users, but only modify their own user account
    permission_classes = [IsAuthenticatedOrReadOnly, IsUserOrReadOnly]


class MessagePagination(PageNumberPagination):
    page_size = 50


# Rest framework api endpoint for viewing all messages
class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["author", "channel", "content", "created_at", "reply_to"]

    # Only allow users to view messages from the channels which they are members of
    # For security reasons
    def get_queryset(self):
        user = self.request.user
        queryset = Message.objects.filter(channel__members=user).order_by("-created_at")
        return queryset


# Rest framework api endpoint for viewing channels that a user is part of
class ChannelViewSet(viewsets.ModelViewSet):
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["channel_name", "members", "owner"]

    # Only allow users to view channels which they are members of
    # For security reasons
    def get_queryset(self):
        user = self.request.user
        queryset = Channel.objects.filter(members=user)
        return queryset


# Rest framework api endpoint for leaving a channel
class LeaveChannelViewSet(views.APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "You are not authenticated"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = LeaveChannelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        User.objects.get(id=request.user.id).channels.get(
            pk=serializer.data["channel"]
        ).delete()
        return Response(serializer.data, status=status.HTTP_200_OK)
