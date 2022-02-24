from datetime import datetime

from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.db.models import Q
from django.contrib.auth import authenticate
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from rest_framework import exceptions
from rest_framework import serializers
from rest_framework.serializers import Serializer, ModelSerializer
from rest_framework.exceptions import NotAuthenticated
from rest_framework.validators import UniqueValidator
from rest_auth.serializers import PasswordResetSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from accounts.models import User, UserProfile, UserFiles, PotentialUser, UserFollowing
from push_notifications.models import Notification
from virtualcoins.models import Brand, Offer, OfferRedemption

from campaign import WAITLIST_CAMPAIGN, MAX_WAITLIST_USERS

from .mixins import MailMixin, FilterAdultContent
from .models import Pitch, PitchScore, ReportPitch, PitchComments, Article


def register_social_user(provider, user_id, email, name):
    filtered_user_by_email = User.objects.filter(email=email)

    if filtered_user_by_email.exists():

        if provider == filtered_user_by_email[0].auth_provider:

            registered_user = authenticate(
                email=email, password=os.environ.get("SOCIAL_SECRET")
            )

            return {
                "username": registered_user.username,
                "email": registered_user.email,
                "tokens": registered_user.tokens(),
            }

        else:
            raise AuthenticationFailed(
                detail="Please continue your login using "
                + filtered_user_by_email[0].auth_provider
            )

    else:
        user = {
            "username": generate_username(name),
            "email": email,
            "password": os.environ.get("SOCIAL_SECRET"),
        }
        user = User.objects.create_user(**user)
        user.is_verified = True
        user.auth_provider = provider
        user.save()

        new_user = authenticate(email=email, password=os.environ.get("SOCIAL_SECRET"))
        return {
            "email": new_user.email,
            "username": new_user.username,
            "tokens": new_user.tokens(),
        }


class ErrorMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=256)


class FacebookSocialAuthSerializer(serializers.Serializer):
    """Handles serialization of facebook related data"""

    auth_token = serializers.CharField()

    def validate_auth_token(self, auth_token):
        user_data = facebook.Facebook.validate(auth_token)

        try:
            user_id = user_data["id"]
            email = user_data["email"]
            name = user_data["name"]
            provider = "facebook"
            return register_social_user(
                provider=provider, user_id=user_id, email=email, name=name
            )
        except Exception as identifier:

            raise serializers.ValidationError(
                "The token  is invalid or expired. Please login again."
            )


class GoogleSocialAuthSerializer(Serializer):
    auth_token = serializers.CharField()

    def validate_auth_token(self, auth_token):
        user_data = google.Google.validate(auth_token)
        try:
            user_data["sub"]
        except:
            raise serializers.ValidationError(
                "The token is invalid or expired. Please login again."
            )

        if user_data["aud"] != os.environ.get("GOOGLE_CLIENT_ID"):

            raise AuthenticationFailed("oops, who are you?")

        user_id = user_data["sub"]
        email = user_data["email"]
        name = user_data["name"]
        provider = "google"

        return register_social_user(
            provider=provider, user_id=user_id, email=email, name=name
        )


class TwitterAuthSerializer(Serializer):
    """Handles serialization of twitter related data"""

    access_token_key = serializers.CharField()
    access_token_secret = serializers.CharField()

    def validate(self, attrs):

        access_token_key = attrs.get("access_token_key")
        access_token_secret = attrs.get("access_token_secret")

        user_info = twitterhelper.TwitterAuthTokenVerification.validate_twitter_auth_tokens(
            access_token_key, access_token_secret
        )

        try:
            user_id = user_info["id_str"]
            email = user_info["email"]
            name = user_info["name"]
            provider = "twitter"
        except:
            raise serializers.ValidationError(
                "The tokens are invalid or expired. Please login again."
            )

        return register_social_user(
            provider=provider, user_id=user_id, email=email, name=name
        )


class LoginSerializer(TokenObtainPairSerializer):
    """
    payload_data:
    {
        "email": "hansdah.roshan@gmail.com",
        "password": "roshan"
    }
    response content:
    HTTP 200 OK
    Allow: POST, OPTIONS
    Content-Type: application/json
    Vary: Accept

    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTY0Mjg0MTIwMywianRpIjoiMGYwZTFkZDg0MGQyNDBkN2JhMDM4YWJkNDA4YjRmNzUiLCJ1c2VyX2lkIjoxfQ.F6-qfPpXOrLIgvv12rlurjjKZ0eKyjA_KVQZ4gLpWNE",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjQyNzU1MTAzLCJqdGkiOiJmM2QwZDNhMTdhZjM0ODFlOTYwYTI2OGY4MzNkYTNiNSIsInVzZXJfaWQiOjF9.4d-Qii8tXdC1Yb9Bg6ldYTS_KNk9uwRJ6VYVeBZdm0E",
        "user_name": "roshan",
        "user_id": 1
    }
    """

    def validate(self, attrs):
        data = super(LoginSerializer, self).validate(attrs)
        data.update(
            {
                "user_id": self.user.id,
                "user_name": self.user.username,
                "user_email": self.user.email,
                "user_mobile": self.user.mobile,
                "full_name": self.user.full_name,
            }
        )
        return data


class RegisterSerializer(ModelSerializer):
    """
    payload_data:
    {
        "email": "testuser4@gmail.com",
        "mobile": "912345600",
        "password": "Champ2424",
        "password2": "Champ2424"
    }
    response_content:
    HTTP 201 Created
    Allow: POST, OPTIONS
    Content-Type: application/json
    Vary: Accept

    {
        "email": "testuser@gmail.com"
    }
    """

    mobile = serializers.CharField(allow_blank=True)
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("email", "password", "password2", "mobile")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def send_email_for_account_activation(self, user):
        mail_subject = "Activate your Champhunt account"

        message = render_to_string(
            "accounts/champhunt_account_activation.html",
            {"user": user, "activation_url": "http://champhunt.com"},
        )
        to_email = user.email
        email = EmailMessage(mail_subject, message, to=[to_email])
        email.send()

    def create(self, validated_data):
        # keep username as email id or mobile no.
        username = validated_data["email"]
        if validated_data.get("mobile"):
            username += "-" + validated_data["mobile"]
        user = User.objects.create(
            username=username,
            email=validated_data["email"],
            mobile=validated_data.get("mobile"),
        )

        user.set_password(validated_data["password"])
        user.save()
        self.send_email_for_account_activation(user)
        return user


class LoggedInProfileSerializer(serializers.ModelSerializer):
    userprofile_id = serializers.ReadOnlyField(source="user.id")

    class Meta:
        model = UserProfile
        fields = ("userprofile_id",)


class UserFilesSerializer(ModelSerializer):
    class Meta:
        model = UserFiles
        exclude = ("user",)

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        return UserFiles.objects.create(**validated_data)


class UserProfileSerializer(ModelSerializer):
    """
    payload_data:
    {
    "kycfiles": {
        "aadhar": null,
        "pancard": null,
        "passport": null,
        "driving_license": null
    },
    "gender": null,
    "first_name": "",
    "last_name": "",
    "is_player": false,
    "player_profile": null,
    "referred_by": null,
    "user": null
    }
    response_content:
    {
    "id": 1,
    "kycfiles": {
        "id": 7,
        "aadhar": "http://127.0.0.1:8001/media/accounts/kycfiles/aadhar/2021/12/12/Aadhar_1_eDJlmpU.pdf",
        "pancard": null,
        "passport": null,
        "driving_license": null
    },
    "gender": "M",
    "first_name": "Roshan",
    "last_name": "Hansdah",
    "is_player": true,
    "player_profile": "Batting Allrounder",
    "referred_by": "",
    "user": 1
    }
    """

    followers_count = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        exclude = ("documents", "friends", "followers", "kycfiles")

    def get_followers_count(self, obj):
        return obj.followers.count()


class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.

    Heavily based on
    https://github.com/tomchristie/django-rest-framework/pull/1268

    Updated for Django REST framework 3.
    """

    def to_internal_value(self, data):
        from django.core.files.base import ContentFile
        import base64
        import six
        import uuid

        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            # Check if the base64 string is in the "data:" format
            if "data:" in data and ";base64," in data:
                # Break out the header from the base64 content
                header, data = data.split(";base64,")

            # Try to decode the file. Return validation error if it fails.
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail("invalid_image")

            # Generate file name:
            file_name = str(uuid.uuid4())[:12]  # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension,)

            data = ContentFile(decoded_file, name=complete_file_name)

        return super(Base64ImageField, self).to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        import imghdr

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension


class PitchSerializer(FilterAdultContent, serializers.ModelSerializer):
    image = Base64ImageField(
        max_length=None,
        use_url=True,
        required=False,
        allow_empty_file=True,
        allow_null=True,
    )

    class Meta:
        model = Pitch
        exclude = ("modified", "shared_user", "shared_body")

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["comments"] = PitchCommentsSerializer(
            instance.pitchcomments_set.all(), many=True
        ).data
        response["user_data"] = UserProfileSerializer(instance.userprofile).data
        if instance.shared_user:
            response["shared_user"] = {
                "name": f"{instance.shared_user.first_name} {instance.shared_user.last_name}",
                "url": "",
            }
        return response

    def validate(self, data):
        image = data.get("image", "")
        if image and self.get_skin_ratio(image) >= 0.5:
            raise serializers.ValidationError(
                {"image": f"nsfw image! -- {self.get_skin_ratio(image)} skin content"}
            )
        return data


class SharePitchSerializer(Serializer):
    """
    { 
        author: {
            name,
            url,
            avatar
        },
        coAuthor: {
            name: coAuthorName,
            url: coAuthorURL
        } = {},
        post: {
            post_id,
            date,
            time,
            content,
            image,
            comments=[],
            runs
        }
    } 
    """

    pitch = PitchSerializer()
    shared_user = serializers.IntegerField()
    shared_body = serializers.CharField(max_length=500, required=False)

    def create(self, validated_data):
        pitch_data = validated_data["pitch"]
        # it's a new pitch set runs to 0
        pitch_data.update(
            {
                "runs": 0,
                "shared_user": get_object_or_404(
                    UserProfile, id=validated_data["shared_user"]
                ),
                "shared_body": validated_data["shared_body"],
            }
        )
        return Pitch.objects.create(**pitch_data)


class PitchCommentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PitchComments
        exclude = ("modified",)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["date"] = datetime.strftime(instance.created, "%d.%m.%Y")
        response["time"] = datetime.strftime(instance.created, "%I:%M %p")
        response["author"] = UserProfileSerializer(instance.userprofile).data
        return response


class PitchScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = PitchScore
        exclude = ("created", "modified")

    def validate(self, data):
        """
        Check that pitch has already been given a score by this user.
        """
        pitch = data["pitch"]
        userprofile = data["userprofile"]
        if pitch.userprofile == userprofile:
            raise serializers.ValidationError(f"You can't score your own pitch")
        if PitchScore.objects.filter(
            pitch_id=pitch.id, userprofile=userprofile
        ).exists():
            raise serializers.ValidationError(
                f"Pitch has already been given score by this user: {userprofile.user.email}"
            )
        return data


class ReportPitchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportPitch
        exclude = ("created", "modified")

    def validate(self, data):
        """
        Check that pitch has already been reported by this user.
        """
        pitch = data["pitch"]
        userprofile = data["userprofile"]
        if ReportPitch.objects.filter(pitch=pitch, userprofile=userprofile).exists():
            raise serializers.ValidationError(f"Pitch has already been reported")
        return data


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    class Meta:
        fields = ["email"]

    def validate(self, attrs):
        email = attrs.get("email")
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {"email": "User with this email id doesnt exist"}
            )
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, max_length=80, write_only=True)
    confirm_password = serializers.CharField(
        min_length=8, max_length=80, write_only=True
    )
    token = serializers.CharField(min_length=1, write_only=True)
    uidb64 = serializers.CharField(min_length=1, write_only=True)

    class Meta:
        fields = ["password", "confirm_password", "token", "uidb64"]

    def validate(self, attrs):
        try:
            password = attrs.get("password")
            token = attrs.get("token")
            uidb64 = attrs.get("uidb64")

            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed("The reset link is invalid", 401)

            user.set_password(password)
            user.save()

            return user
        except Exception as e:
            raise AuthenticationFailed("The reset link is invalid", 401)
        return super().validate(attrs)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

    class Meta:
        fields = ["old_password", "new_password", "confirm_new_password"]

    def validate(self, attrs):
        min_length = 8
        old_password = attrs.get("old_password")
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")

        if old_password == new_password:
            raise serializers.ValidationError(
                {"new_password": "new password is same as old password"}
            )

        if new_password != confirm_new_password:
            raise serializers.ValidationError(
                {"confirm_new_password": "password doesnt match"}
            )

        if len(new_password) < min_length:
            raise serializers.ValidationError(
                _("Password must be at least {0} characters " "long.").format(
                    min_length
                )
            )
        # check for digit
        if not any(char.isdigit() for char in new_password):
            raise serializers.ValidationError(
                _("Password must contain at least 1 digit.")
            )

        # check for letter
        if not any(char.isalpha() for char in new_password):
            raise serializers.ValidationError(
                _("Password must contain at least 1 letter.")
            )
        return attrs


class BrandsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class OffersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = "__all__"

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["brand"] = BrandsSerializer(instance.brand).data
        return response


class OfferRedemptionSerializer(serializers.ModelSerializer):
    """
        Assumption:
            1000 runs => 10 crickcoins
    
        user can redeem offers
    """

    class Meta:
        model = OfferRedemption
        exclude = ("created", "modified")

    def validate(self, attrs):
        offer = attrs["offer"]
        userprofile = attrs["userprofile"]
        crickcoins_required = offer.crickcoins_required
        userprofile_runs = userprofile.runs
        required_runs_to_redeem = crickcoins_required * 100
        if userprofile_runs < required_runs_to_redeem:
            raise serializers.ValidationError(
                (
                    f"User {userprofile.user.email} doesnt have enough crickcoins to redeem this offer {offer.name}"
                )
            )
        return attrs

    def create(self, validated_data):
        return OfferRedemption.objects.create(**validated_data)


class PotentialUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    mobile = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        email = attrs.get("email")
        mobile = attrs.get("mobile")
        if not email and not mobile:
            raise serializers.ValidationError(
                (f"Atleast one of the fields is required: Email or Mobile")
            )
        if (email and User.objects.filter(email=email).exists()) or (
            PotentialUser.objects.filter(email=email).exists()
        ):
            raise serializers.ValidationError(
                {
                    "email": "We have already sent mail to this email id "
                    "or this email already exists with us!"
                }
            )
        if mobile and User.objects.filter(mobile=mobile).exists():
            raise serializers.ValidationError(
                {"mobile": "This mobile no is already with us"}
            )
        if (
            PotentialUser.objects.filter(source=WAITLIST_CAMPAIGN).count()
            >= MAX_WAITLIST_USERS
        ):
            raise serializers.ValidationError(("Waitlist Campaign is over."))
        return attrs

    def create(self, validated_data):
        return PotentialUser.objects.create(**validated_data)


class SearchSerializer(Serializer):
    profiles = UserProfileSerializer(many=True)
    pitches = PitchSerializer(many=True)


class NotificationsSerializer(ModelSerializer):
    class Meta:
        model = Notification
        exclude = ("modified",)


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    default_error_message = {"bad_token": ("Token is expired or invalid")}

    def validate(self, attrs):
        self.token = attrs["refresh_token"]
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail("bad_token")


class ArticleSerializer(ModelSerializer):
    class Meta:
        model = Article
        exclude = ("modified",)


class FollowRequestSerializer(ModelSerializer):
    class Meta:
        model = UserFollowing
        exclude = ("modified",)

    def validate(self, attrs):
        if attrs["user"] == attrs["following_user"]:
            raise serializers.ValidationError(("Can't add yourself as follower."))
        if UserFollowing.objects.filter(
            user=attrs["user"], following_user=attrs["following_user"]
        ).exists():
            raise serializers.ValidationError(
                ("This follow combination already exists")
            )
        return attrs
