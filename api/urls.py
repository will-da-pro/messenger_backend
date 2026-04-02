from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserCreateView, UserViewSet, MessageViewSet, ChannelViewSet, UserLoginView, UserChangePasswordView, \
    LeaveChannelViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'messages', MessageViewSet, basename='messages')
router.register(r'channels', ChannelViewSet, basename='channels')

# Adds all the /api/ urls for rest framework
urlpatterns = [
    path('register/', UserCreateView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('change-password/', UserChangePasswordView.as_view(), name='user-change-password'),
    path('leave-channel/', LeaveChannelViewSet.as_view(), name='leave-channel'),
    path('', include(router.urls)),
]
