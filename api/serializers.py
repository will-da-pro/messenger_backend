from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import User, Message, Channel


# All serializers allow for the conversion between django types and json, for communication over the REST api


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "first_name", "last_name"]
        read_only_fields = ["id"]
        extra_kwargs = {"password": {"write_only": True}}

    # Validate the password with django built in validation (not too short, not too common, etc.)
    @staticmethod
    def validate_password(value):
        try:
            validate_password(password=value, user=None)

        except serializers.ValidationError as e:
            raise e

        return value

    # All of these fields must be present to create a new useer
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )

        return user


class LoginSerializer(serializers.Serializer):
    # These fields are required to log in
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    repeat_password = serializers.CharField(required=True)

    # Ensure the old password is actually correct
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    # Validate the new password with Django built in validation
    @staticmethod
    def validate_new_password(value):
        try:
            validate_password(password=value, user=None)
        except serializers.ValidationError as e:
            raise e

        return value

    # Ensure the password and confirmation are actually equal
    def validate(self, attrs):
        new_password = attrs.get("new_password")
        repeat_password = attrs.get("repeat_password")

        if new_password != repeat_password:
            raise serializers.ValidationError()

        return attrs

    # Save the new password to the database
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = ["id"]

    def create(self, validated_data):
        # Required fields to create message
        message = Message.objects.create(
            author=validated_data["author"],
            content=validated_data["content"],
            channel=validated_data["channel"],
            reply_to=validated_data["reply_to"],
        )

        return message


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = "__all__"
        read_only_fields = ["id"]


class LeaveChannelSerializer(serializers.Serializer):
    channel = serializers.UUIDField()
