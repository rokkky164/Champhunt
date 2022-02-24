from django.contrib import admin
from django.contrib.admin import ModelAdmin

from .models import Notification


class NotificationAdmin(ModelAdmin):
    raw_id_fields = ["userprofile"]


admin.site.register(Notification, NotificationAdmin)
