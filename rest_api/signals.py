import json
from datetime import datetime

import channels.layers
from asgiref.sync import async_to_sync

from django.db.models.signals import post_save
from django.dispatch import receiver

from push_notifications.models import Notification

from .models import Pitch, PitchScore, PitchComments


@receiver(post_save, sender=PitchScore)
def update_pitch_runs(sender, instance, created, **kwargs):
    if created:
        pitch = instance.pitch
        userprofile = instance.userprofile
        pitch_author = pitch.userprofile
        notification_data = {
            "userprofile": pitch_author,
            "notification": f"{userprofile.first_name} gave {instance.runs_awarded} runs to your pitch",
        }
        Notification.objects.create(**notification_data)
        pitch.runs += instance.runs_awarded
        pitch.save()
        pitch_author.runs += instance.runs_awarded
        pitch_author.save()

        layer = channels.layers.get_channel_layer()
        async_to_sync(layer.group_send)(
            f"pitch_score-{pitch.id}",
            {
                "type": "get.pitch.runs",
                "data": json.dumps(
                    {"pitch_id": pitch.id, "runs_awarded": instance.runs_awarded},
                ),
            },
        )


@receiver(post_save, sender=PitchComments)
def update_pitch_comment_details(sender, instance, created, **kwargs):
    if created:
        pitch = instance.pitch
        pitch_author = pitch.userprofile
        userprofile = instance.userprofile
        notification_data = {
            "userprofile": pitch_author,
            "notification": f"{userprofile.first_name} commented on your pitch",
        }
        Notification.objects.create(**notification_data)
        layer = channels.layers.get_channel_layer()
        async_to_sync(layer.group_send)(
            f"pitch_comment-{pitch.id}",
            {
                "type": "get.pitch.comment",
                "data": json.dumps({
                    "pitch_id": pitch.id,
                    "comment": instance.comment,
                    "userprofile": userprofile.id,
                    "date": datetime.strftime(instance.created, "%d.%m.%Y"),
                    "time": datetime.strftime(instance.created, "%I:%M %p"),
                    "author": {
                        "first_name": userprofile.first_name,
                        "last_name": userprofile.last_name
                    }
                })
            },
        )


@receiver(post_save, sender=Pitch)
def submit_pitch_details(sender, instance, created, **kwargs):
    pitch = instance
    if created and pitch.shared_user:
        pitch_author = pitch.userprofile
        notification_data = {
            "userprofile": pitch_author,
            "notification": f"{pitch.shared_user.first_name} shared your pitch",
        }
        Notification.objects.create(**notification_data)
    layer = channels.layers.get_channel_layer()
    async_to_sync(layer.group_send)(
        "pitch_post",
        {
            "type": "get.posted.pitch.data",
            "data": json.dumps({"pitch_id": pitch.id,},),
        },
    )
