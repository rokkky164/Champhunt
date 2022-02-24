from django.db import models
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

from jsonfield import JSONField
from collections import OrderedDict


PITCH_FILES_VALIDATOR = FileExtensionValidator(
    allowed_extensions=["jpg", "jpeg", "png", "pdf"]
)

VISIBLE_TO_CHOICES = (("Friends", "Friends"), ("Public", "Public"))

FRIEND_REQUEST_STATUSES = (
    (0, "Pending"),
    (1, "Accepted"),
    (2, "Declined"),
    (3, "Cancelled"),
    (4, "Unfriended"),
)

REPORT_PITCH_CHOICES = (
    ("Harassment", "Harassment"),
    ("Spam", "Spam"),
    ("Plagiarism", "Plagiarism"),
    ("Poorly Written", "Poorly Written"),
    ("Factually Incorrect", "Factually Incorrect"),
    ("Adult Content", "Adult Content"),
)

ARTICLE_TYPES = (
    ("INTERVIEWS", "INTERVIEWS"),
    ("TRIVIA", "TRIVIA"),
    ("MOTIVATION", "MOTIVATION"),
)


class AbstractDateTimeModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Pitch(AbstractDateTimeModel):
    message = models.TextField(blank=True, default="")
    visible_to = models.CharField(
        max_length=50, choices=VISIBLE_TO_CHOICES, default=VISIBLE_TO_CHOICES[1][0]
    )
    image = models.FileField(
        validators=[PITCH_FILES_VALIDATOR],
        upload_to="champhunt/pitches/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    url_link = models.URLField(max_length=500, null=True, blank=True)
    userprofile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    runs = models.IntegerField(default=0)
    tags = models.CharField(max_length=500, blank=True, null=True)
    shared_body = models.TextField(blank=True, default="")
    shared_user = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
    )

    def __str__(self):
        return f"{self.userprofile.user.email}-{self.message[:20]}"


class PitchComments(AbstractDateTimeModel):
    pitch = models.ForeignKey(Pitch, on_delete=models.CASCADE)
    userprofile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    comment = models.TextField()

    def __str__(self):
        return f"{self.userprofile.user.email}-{self.pitch.message[:10]}-{self.comment[:20]}"


class PitchScore(AbstractDateTimeModel):
    pitch = models.ForeignKey(Pitch, on_delete=models.CASCADE)
    userprofile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    runs_awarded = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.userprofile.user.email}-{self.pitch.message[:10]}"


class ReportPitch(AbstractDateTimeModel):
    pitch = models.ForeignKey(Pitch, on_delete=models.CASCADE)
    userprofile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    report_type = models.CharField(max_length=50, choices=REPORT_PITCH_CHOICES)
    report_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return (
            f"{self.userprofile.user.email}--{self.report_type}--{self.report_message}"
        )


class Article(AbstractDateTimeModel):
    title = models.CharField(max_length=140)
    body = models.TextField()
    image = models.ImageField(upload_to="champhunt/articles/%Y/%m/%d/")
    author = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    article_type = models.CharField(
        max_length=50, choices=ARTICLE_TYPES, blank=True, null=True
    )

    def __str__(self):
        return f"{self.author}--{self.title}"
