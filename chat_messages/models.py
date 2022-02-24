import random

from django.db import models

from rest_api.models import AbstractDateTimeModel


def get_room_id():
    return "".join(random.choices("ABCDEFGHIJ1234567890", k=10))


class ThreadManager(models.Manager):
    def get_or_create_personal_thread(self, user1, user2):
        threads = self.get_queryset().filter(thread_type="personal")
        threads = threads.filter(users__in=[user1.id, user2.id]).distinct()
        threads = threads.annotate(user_count=Count("users")).filter(user_count=2)
        if threads.exists():
            return threads.first()
        else:
            thread = self.create(thread_type="personal")
            thread.users.add(user1)
            thread.users.add(user2)
            return thread

    def by_user(self, user):
        return self.get_queryset().filter(users__in=[user])


class Thread(AbstractDateTimeModel):
    THREAD_TYPE = (("personal", "Personal"), ("group", "Group"))

    name = models.CharField(max_length=50, null=True, blank=True)
    thread_type = models.CharField(max_length=15, choices=THREAD_TYPE, default="group")
    users = models.ManyToManyField("accounts.User")
    has_unread = models.BooleanField(default=False)

    objects = ThreadManager()

    def __str__(self) -> str:
        if self.thread_type == "personal" and self.users.count() == 2:
            return f"{self.users.first()} and {self.users.last()}"
        return f"{self.name}"


class ChatMessage(AbstractDateTimeModel):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    sender = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    text = models.TextField(blank=False, null=False)
    image = models.ImageField(upload_to="chatmessages/%Y/%m/%d", blank=True, null=True)
    is_read = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"From <Thread - {self.thread}>"


class ChatRoom(models.Model):
    room_id = models.CharField(default=get_room_id, max_length=10)
    participants = models.ManyToManyField(
        "accounts.User", related_name="chats", blank=True
    )
    messages = models.ManyToManyField(ChatMessage, blank=True)

    def __str__(self):
        return self.room_id
