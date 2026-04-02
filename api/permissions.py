from rest_framework import permissions


# Ensures that users can only change their own profiles
class IsUserOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allows read requests for anyone
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        return obj == request.user


# Ensures only the owner of a channel can change it
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allows read requests for anyone
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        return obj.owner == request.user

