import numpy as np
import random

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save, post_save
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from django.template.loader import get_template
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.core.validators import RegexValidator
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from jsonfield import JSONField
from collections import OrderedDict

from push_notifications.models import Notification

from rest_api.models import AbstractDateTimeModel


ALPHANUMERIC_STRING = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
KYC_FILES_VALIDATOR = FileExtensionValidator(
    allowed_extensions=["jpg", "jpeg", "png", "pdf"]
)
PROFILE_PIC_VALIDATOR = FileExtensionValidator(
    allowed_extensions=["jpg", "jpeg", "png"]
)
GENDER_CHOICES = (("M", "Male"), ("F", "Female"))
PLAYING_ROLES = (
    ("Batsman", "Batsman"),
    ("Bowler", "Bowler"),
    ("Batting Allrounder", "Batting Allrounder"),
    ("Bowler Allrounder", "Bowler Allrounder"),
)
REFERRAL_CHOICES = (
    ("CricTrade Event", "CricTrade Event"),
    ("Friend Invitation", "Friend Invitation"),
)


class UserManager(BaseUserManager):
    def create_user(
        self,
        username,
        email,
        password=None,
        full_name=None,
        is_active=True,
        is_staff=False,
        is_superuser=False,
        mobile=None,
    ):
        if not username:
            raise ValueError("Username taken.")
        if not email:
            raise ValueError("Email required.")
        if not password:
            raise ValueError("Password required.")

        user_obj = self.model(
            username=username, email=self.normalize_email(email), full_name=full_name
        )
        user_obj.mobile = mobile
        user_obj.set_password(password)
        user_obj.is_active = is_active
        user_obj.staff = is_staff
        user_obj.is_superuser = is_superuser
        user_obj.cash = 10000.00
        user_obj.save(using=self._db)
        return user_obj

    def create_staffuser(self, username, email, full_name=None, password=None):
        user = self.create_user(
            username, email, password=password, full_name=full_name, is_staff=True
        )
        return user

    def create_superuser(
        self, username, email, full_name=None, password=None, mobile=None
    ):
        user = self.create_user(
            username,
            email,
            password=password,
            full_name=full_name,
            mobile=mobile,
            is_staff=True,
            is_superuser=True,
        )
        return user


class User(AbstractBaseUser):
    username = models.CharField(unique=True, max_length=50)
    email = models.EmailField(unique=True, max_length=255)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    cash = models.DecimalField(max_digits=20, decimal_places=2, default=1000)
    escrow = models.DecimalField(
        max_digits=20, decimal_places=2, default=0
    )  # When user places a buy order, the order value will be subtracted from his cash and stored here. If the order is unsuccessful or cancelled, this amount will be added back to cash.
    is_active = models.BooleanField(default=False)
    staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    mobile = models.CharField(
        max_length=15,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Phone number entered is invalid",
                code="invalid_phone_number",
            ),
        ],
    )
    referral_code = models.CharField(max_length=25, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["mobile", "username"]

    objects = UserManager()

    def __str__(self):
        return self.username

    def get_full_name(self):
        if self.full_name:
            return self.full_name
        return self.username

    def get_short_name(self):
        return self.username

    def has_perm(self, perm, object=None):
        """Does the user have a specific permission?"""
        return True

    def has_module_perms(self, app_label):
        """Does the user have permissions to view the app 'app_label'?"""
        return True

    @property
    def is_staff(self):
        return self.staff


class UserFiles(models.Model):
    aadhar = models.FileField(
        validators=[KYC_FILES_VALIDATOR],
        upload_to="accounts/kycfiles/aadhar/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    pancard = models.FileField(
        validators=[KYC_FILES_VALIDATOR],
        upload_to="accounts/kycfiles/pancard/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    passport = models.FileField(
        validators=[KYC_FILES_VALIDATOR],
        upload_to="accounts/kycfiles/passport/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    driving_license = models.FileField(
        validators=[KYC_FILES_VALIDATOR],
        upload_to="accounts/kycfiles/driving_license/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.FileField(
        validators=[PROFILE_PIC_VALIDATOR],
        upload_to="accounts/profile_pics/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    kycfiles = models.ForeignKey(
        UserFiles, on_delete=models.CASCADE, blank=True, null=True
    )
    gender = models.CharField(
        max_length=20, choices=GENDER_CHOICES, null=True, blank=True
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    documents = JSONField(
        load_kwargs={"object_pairs_hook": OrderedDict}, default=OrderedDict()
    )  # >  {"aadhar": "1234567889", "pancard": "ABCD12345M", "passport": "K12345678K"}
    address = models.CharField(max_length=200, blank=True, default="")
    address2 = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    zip_code = models.CharField(max_length=100, blank=True, default="")
    is_player = models.BooleanField(default=False)
    player_profile = models.CharField(
        max_length=50, choices=PLAYING_ROLES, blank=True, null=True
    )
    referred_by = models.CharField(
        max_length=50, choices=REFERRAL_CHOICES, blank=True, null=True
    )
    runs = models.IntegerField(default=100)
    friends = models.ManyToManyField("self", related_name="friends", blank=True)
    followers = models.ManyToManyField("self", related_name="followers", blank=True)
    crickcoins = models.IntegerField(default=1000)

    def __str__(self):
        return self.user.username


@receiver(m2m_changed, sender=UserProfile.friends.through)
def handle_user_profile_friends(sender, **kwargs):
    instance = kwargs.pop("instance", None)
    pk_set = kwargs.pop("pk_set", None)
    action = kwargs.pop("action", None)
    if action == "pre_add" and instance.id in pk_set:
        raise ValidationError(f"Can't add yourself as friend.")


@receiver(m2m_changed, sender=UserProfile.followers.through)
def handle_user_profile_followers(sender, **kwargs):
    instance = kwargs.pop("instance", None)
    pk_set = kwargs.pop("pk_set", None)
    action = kwargs.pop("action", None)
    if action == "pre_add" and instance.id in pk_set:
        raise ValidationError(f"Can't add yourself as follower.")


class Invitation(models.Model):
    INVITED = "Invited"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    STATUS_CHOICES = ((INVITED, INVITED), (ACCEPTED, ACCEPTED), (DECLINED, DECLINED))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=INVITED)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE)
    to_users = JSONField(
        load_kwargs={"object_pairs_hook": OrderedDict}, default=OrderedDict()
    )

    def __str__(self):
        return self.from_user.username


def validate_potential_user(self):
    if User.objects.filter(email=user.email).exists():
        raise ValidationError(
            f"User with this email id: {user.email} exists in the database"
        )


class PotentialUser(AbstractDateTimeModel):
    email = models.EmailField(unique=True, max_length=255, null=True)
    mobile = models.CharField(
        max_length=15,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Phone number entered is invalid",
                code="invalid_phone_number",
            ),
        ],
    )
    source = models.CharField(max_length=255)
    waitlist_amount = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.email}--{self.mobile}-{self.source}"

    def save(self, *args, **kwargs):
        if not self.email and not self.mobile:
            raise ValidationError(
                f"Atleast one of the fields is required: Email or Mobile"
            )
        super().save(*args, **kwargs)


class FriendRequest(models.Model):
    PENDING = 0
    ACCEPTED = 1
    DECLINED = 2
    CANCELLED = 3
    UNFRIENDED = 4
    from_user = models.ForeignKey(
        "accounts.UserProfile", related_name="from_user", on_delete=models.CASCADE
    )
    to_user = models.ForeignKey(
        "accounts.UserProfile", related_name="to_user", on_delete=models.CASCADE
    )
    status = models.IntegerField(default=0)


class UserFollowing(AbstractDateTimeModel):
    user = models.ForeignKey(
        "accounts.UserProfile", related_name="user_follower", on_delete=models.CASCADE
    )
    following_user = models.ForeignKey(
        "accounts.UserProfile", related_name="user_following", on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "following_user"], name="unique_followers"
            )
        ]

        ordering = ["-created"]

    def __str__(self):
        return f"{self.user_id} follows {self.following_user_id}"



@receiver(post_save, sender=UserFollowing)
def notify_when_someone_follows(sender, instance, created, **kwargs):
    if created:
        following_user = instance.following_user
        user_who_is_following = instance.user
        notification_data = {
            "userprofile": following_user,
            "notification": f"{user_who_is_following} is following you now",
        }
        Notification.objects.create(**notification_data)