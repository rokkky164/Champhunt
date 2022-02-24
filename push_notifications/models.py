import json
import channels.layers

from django.db import models

from asgiref.sync import async_to_sync

from rest_api.models import AbstractDateTimeModel


class Notification(AbstractDateTimeModel):
    userprofile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    notification = models.TextField()
    is_seen = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        channel_layer = channels.layers.get_channel_layer()
        notification_objs_count = Notification.objects.filter(is_seen=False).count()
        data = {
            "notification_count": notification_objs_count,
            "current_notification": self.notification,
            "userprofile_id": self.userprofile.id,
        }
        async_to_sync(channel_layer.group_send)(
            f"notification_{self.userprofile.id}",
            {"type": "send_notification", "value": json.dumps(data)},
        )
        super(Notification, self).save(*args, **kwargs)
