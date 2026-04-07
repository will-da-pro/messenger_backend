import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator

# Create your models here.

# All models are translated into SQL tables


# Custom User model, inheriting from built in Django user model
class User(AbstractUser):
    # Use UUID instead of sequential ids for security
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Email and username fields must be unique
    email = models.EmailField(
        unique=True,
        blank=False,
        null=False,
        error_messages={"unique": "A user with that email already exists."},
    )

    username = models.CharField(
        max_length=150,
        unique=True,
        blank=False,
        null=False,
        validators=[MinLengthValidator(3)],
        error_messages={"unique": "A user with that username already exists."},
        help_text="Required. 3–150 characters. Letters, digits and @.+-_ only.",
    )

    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Require the user to set an email to register
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username


# Model for channels
class Channel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel_name = models.CharField(
        max_length=150,
        unique=True,
        blank=False,
    )

    channel_description = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    # Channels can have many members
    # This creates a separate database to ensure the databases are normalised
    members = models.ManyToManyField(User, related_name="channels")

    # Channels must have one owner
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_channels")

    def __str__(self):
        return self.channel_name


# Model for messages
class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="messages")

    # 2000-character limit for text
    content = models.CharField(
        max_length=2000,
        blank=False,
        null=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, related_name="replies", null=True)
    edited = models.BooleanField(default=False)
