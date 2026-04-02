from django.contrib import admin
from .models import User, Channel, Message

# Register your models here.
# Allow models to be accessed on the admin panel
admin.site.register(User)
admin.site.register(Channel)
admin.site.register(Message)
