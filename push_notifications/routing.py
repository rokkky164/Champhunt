from django.urls import re_path

from . import consumers


# https://github.com/priyanshu2015/django-channels-celery
push_notifications_urlpatterns = [
    re_path(
        r"ws/notification/(?P<user_id>\w+)/$", consumers.NotificationConsumer.as_asgi()
    ),
]
