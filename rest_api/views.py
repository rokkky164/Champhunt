import itertools
import random

from datetime import datetime, timedelta
from dateutil import parser
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import smart_bytes, force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from django.core.mail import EmailMessage
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    GenericAPIView,
    UpdateAPIView,
    ListCreateAPIView,
)
from rest_framework import serializers
from rest_framework.viewsets import ViewSet, ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.mixins import RetrieveModelMixin
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.parsers import MultiPartParser, FormParser

from accounts.models import User, UserProfile, PotentialUser
from accounts.invitations import InvitationUtil
from virtualcoins.models import Brand, Offer, OfferRedemption
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    LoginSerializer,
    LoggedInProfileSerializer,
    PotentialUserSerializer,
    GoogleSocialAuthSerializer,
    FacebookSocialAuthSerializer,
    TwitterAuthSerializer,
    PitchSerializer,
    PitchScoreSerializer,
    ReportPitchSerializer,
    PitchCommentsSerializer,
    ResetPasswordSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    SearchSerializer,
    BrandsSerializer,
    OffersSerializer,
    OfferRedemptionSerializer,
    SharePitchSerializer,
    NotificationsSerializer,
    LogoutSerializer,
    ArticleSerializer,
    FollowRequestSerializer,
)

from .mixins import MailMixin
from .models import Pitch, PitchScore, ReportPitch, PitchComments, Article


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class RegisterAPIView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class Limit50MaxLimit500Pagination(LimitOffsetPagination):
    max_limit = 500
    default_limit = 50


class Limit10MaxLimit100Pagination(LimitOffsetPagination):
    max_limit = 100
    default_limit = 10


class LoggedInUserProfileAPIView(APIView):
    def get(self, request):
        profile = get_object_or_404(UserProfile, user_id=self.request.user.id)
        return Response(
            {"profile_id": profile.id, "profile_crickcoins": profile.crickcoins}
        )


class UserReadOnlyViewSet(ReadOnlyModelViewSet):
    queryset = UserProfile.objects.select_related("user").order_by("id")
    serializer_class = UserProfileSerializer
    pagination_class = Limit50MaxLimit500Pagination


class UserProfileViewSet(ModelViewSet):
    queryset = (
        UserProfile.objects.select_related("user")
        .prefetch_related("followers")
        .order_by("id")
    )
    serializer_class = UserProfileSerializer
    http_method_names = ["post", "put", "patch", "options"]
    resource_name = "user-profile"

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = UserProfileSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        userprofile = serializer.save()
        return Response(
            data={"user_profile": userprofile.id}, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """
            {
                "address": "Naya gali",
                "state": "Karnataka",
                "city": "New city"
            }
        """
        data = request.data
        serializer = UserProfileSerializer(
            instance=self.get_object(), data=data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.instance
        for field, value in serializer.validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return Response(
            data={"userprofile": instance.id}, status=status.HTTP_202_ACCEPTED
        )


class PitchReadOnlyViewSet(ReadOnlyModelViewSet):
    serializer_class = PitchSerializer
    pagination_class = Limit10MaxLimit100Pagination

    def get_queryset(self):
        pitches = Pitch.objects.select_related("userprofile")
        if self.request.query_params.get("filter") == "user":
            return pitches.filter(userprofile__user__id=self.request.user.id).order_by(
                "-id"
            )
        elif self.request.query_params.get("filter") == "friends":
            profile = UserProfile.objects.get(id=self.request.user.id)
            friends = [p.id for p in profile.friends.all()]
            return (
                pitches.exclude(userprofile_id=profile.id)
                .filter(userprofile__friends__id__in=friends)
                .order_by("-id")
            )
        return pitches.order_by("-id")


class PitchViewSet(ModelViewSet):
    queryset = Pitch.objects.select_related("userprofile").order_by("id")
    serializer_class = PitchSerializer
    http_method_names = ["post", "put", "patch", "options"]
    resource_name = "submit-pitch"
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = PitchSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        pitch = serializer.save()
        return Response(data={"pitch": pitch.id}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
            {
                "address": "Naya gali",
                "state": "Karnataka",
                "city": "New city"
            }
        """
        data = request.data
        serializer = PitchSerializer(
            instance=self.get_object(), data=data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.instance
        for field, value in serializer.validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return Response(data={"pitch": pitch.id}, status=status.HTTP_202_ACCEPTED)


class SharePitchViewSet(ModelViewSet):
    """
        {'pitch_id': '378290', 'shared_user': '1', 'shared_body': 'aa'}
    """

    queryset = Pitch.objects.select_related("userprofile", "shared_user").all()
    serializer_class = SharePitchSerializer
    http_method_names = ["post", "options"]
    resource_name = "share-pitch"

    def create(self, request, *args, **kwargs):
        data = request.data
        pitch = get_object_or_404(Pitch, pk=data["pitch_id"])
        shared_user = get_object_or_404(UserProfile, pk=data["shared_user"])
        data["pitch"] = PitchSerializer(pitch).data
        serializer = SharePitchSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        shared_post = serializer.save()
        validated_post_data = PitchSerializer(shared_post).data
        response = {
            "author": {
                "name": validated_post_data["user_data"]["first_name"]
                + " "
                + validated_post_data["user_data"]["last_name"],
                "url": "",
                "avatar": "https://i.pravatar.cc/45",
            },
            "post": {
                "post_id": shared_post.id,
                "date": datetime.strftime(shared_post.created, "%d.%m.%Y"),
                "time": datetime.strftime(shared_post.created, "%I:%M %p"),
                "content": shared_post.message,
                "runs": shared_post.runs,
                "image": shared_post.image if shared_post.image else None,
            },
            "coAuthor": {
                "name": f"{shared_post.shared_user.first_name} {shared_post.shared_user.last_name}",
                "url": "",
                "content": shared_post.shared_body,
            },
        }
        return Response(data=response, status=status.HTTP_201_CREATED)


class DynamicSearchFilter(filters.SearchFilter):
    def get_search_fields(self, view, request):
        return request.GET.getlist("search_fields", [])


# https://medium.com/swlh/searching-in-django-rest-framework-45aad62e7782
class SearchPitchesAPIView(ListAPIView):
    """
        search using pitches text, tags
    """

    serializer_class = PitchSerializer

    params_mapping = {
        "message": "message",
        "tags": "tags",
    }

    def get_queryset(self):
        """
        This view should return a list of all the pitches based on search term/ query params
        """
        if self.request.query_params:
            pitch_fields = [field.name for field in Pitch._meta.get_fields()]
            for field in list(self.request.query_params.keys()):
                if field not in self.params_mapping:
                    raise serializers.ValidationError(
                        {
                            field: "available search fields \n"
                            + ", ".join([field for field in self.params_mapping])
                        }
                    )
        search_params = Q()
        for param in list(self.request.query_params):
            search_term = self.request.query_params[param]
            if param in self.params_mapping:
                param = self.params_mapping[param]
            search_params |= Q(**{param + "__icontains": search_term})
        return Pitch.objects.filter(search_params)[:1000]


class SearchUsersAPIView(ListAPIView):
    """
        search using users
    """

    serializer_class = UserProfileSerializer
    params_mapping = {
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "user__email",
        "username": "user__username",
    }

    def get_queryset(self):
        """
        This view should return a list of all the users
        """
        if self.request.query_params:
            user_profile_fields = [
                field.name for field in UserProfile._meta.get_fields()
            ]
            for field in list(self.request.query_params.keys()):
                if field not in self.params_mapping:
                    raise serializers.ValidationError(
                        {
                            field: "available search fields \n"
                            + ", ".join([field for field in self.params_mapping])
                        }
                    )
        search_params = Q()
        for param in list(self.request.query_params):
            search_term = self.request.query_params[param]
            if param in self.params_mapping:
                param = self.params_mapping[param]
            search_params |= Q(**{param + "__icontains": search_term})
        return UserProfile.objects.filter(search_params)[:1000]


class SearchAPIView(ListAPIView):
    profile_serializer_class = UserProfileSerializer
    pitch_serializer_class = PitchSerializer
    pitch_params_mapping = {
        "message": "message",
        "tags": "tags",
    }
    profile_params_mapping = {
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "user__email",
        "username": "user__username",
    }

    def get_pitch_queryset(self):
        """
        This should return a list of all the pitches based on search term/ query params
        """
        if self.request.query_params.get("search_term"):
            search_term = self.request.query_params["search_term"]
            search_params = Q()
            for param in list(self.pitch_params_mapping.values()):
                search_params |= Q(**{param + "__icontains": search_term})
            return Pitch.objects.filter(search_params).order_by("-id")[:100]
        return Pitch.objects.none()

    def get_profile_queryset(self):
        """
        This should return a list of all the users
        """
        if self.request.query_params.get("search_term"):
            search_term = self.request.query_params["search_term"]
            search_params = Q()
            for param in list(self.profile_params_mapping.values()):
                search_params |= Q(**{param + "__icontains": search_term})
            return UserProfile.objects.filter(search_params).order_by("-id")[:3]
        return UserProfile.objects.none()

    def get(self, request, *args, **kwrgs):
        pitches = self.get_pitch_queryset()
        profiles = self.get_profile_queryset()
        pitch_serializer = self.pitch_serializer_class(pitches, many=True)
        profile_serializer = self.profile_serializer_class(profiles, many=True)

        return Response(
            {"pitches": pitch_serializer.data, "profiles": profile_serializer.data,}
        )


class PitchCommentReadOnlyViewSet(ReadOnlyModelViewSet):
    serializer_class = PitchCommentsSerializer
    pagination_class = Limit50MaxLimit500Pagination

    def get_queryset(self):
        pitch_id = self.request.query_params.get("pitch")
        if pitch_id:
            return PitchComments.objects.select_related("pitch", "userprofile").filter(
                pitch_id=pitch_id
            )
        return PitchComments.objects.select_related("pitch", "userprofile").all()


class PitchCommentViewSet(ModelViewSet):
    serializer_class = PitchCommentsSerializer
    queryset = PitchComments.objects.all()
    pagination_class = Limit50MaxLimit500Pagination
    http_method_names = ["post", "patch", "put"]


class UserPitchScoreViewSet(ModelViewSet):
    serializer_class = PitchScoreSerializer
    queryset = PitchScore.objects.all()
    pagination_class = Limit50MaxLimit500Pagination


class ReportPitchViewSet(ModelViewSet):
    serializer_class = ReportPitchSerializer
    queryset = ReportPitch.objects.all()
    pagination_class = Limit50MaxLimit500Pagination


class NotificationsReadOnlyViewSet(ViewSet):
    def retrieve(self, request, pk=None):
        today = datetime.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        queryset = NotificationsSerializer.Meta.model.objects.filter(
            userprofile_id=pk, created__gte=start
        )
        if not queryset:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = NotificationsSerializer(queryset, many=True)
            validated_data = serializer.data
            notifications = []
            response = [{"label": "Today", "items": []}]
            for elem in validated_data:
                created_date_obj = parser.parse(elem["created"])
                if created_date_obj.date() == today.date():
                    response[0]["items"].append(
                        {
                            "avatar": "./avatar.png",
                            "content": elem["notification"],
                            "time": datetime.strftime(
                                created_date_obj, "%dth %B, %I:%M %p"
                            ),
                            "postimg": "./postimg.png",
                        }
                    )
                else:
                    response.append({"label": "This Week", "items": []})
                    response[1]["items"].append(
                        {
                            "avatar": "./avatar.png",
                            "content": elem["notification"],
                            "time": datetime.strftime(
                                created_date_obj, "%dth %B, %I:%M %p"
                            ),
                            "postimg": "./postimg.png",
                        }
                    )
            return Response(response, status=status.HTTP_200_OK)


class LogoutAPIView(GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordAPIView(GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        email = request.data.get("email", "")
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)
            current_site = get_current_site(request=request).domain
            relative_link = reverse(
                "accounts:password_reset_confirm",
                kwargs={"uidb64": uidb64, "token": token},
            )
            absolute_url = f"http://{current_site}{relative_link}"
            email_body = (
                "Hello, \n Use link below to reset your password  \n" + absolute_url
            )
            mail_subject = "Reset your password"
            email = EmailMessage(mail_subject, email_body, to=[email])
            email.send()
            return Response(
                {"success": "We have sent you a link to reset your password"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"failed": "We don't have this email id"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PasswordResetConfirmAPIView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, uidb64, token):
        redirect_url = request.GET.get("redirect_url")
        user_pk = smart_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(id=user_pk)

        if PasswordResetTokenGenerator().check_token(user, token):
            return Response(
                {"success": "password reset done successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(UpdateAPIView):
    """
    An endpoint for changing password.
    """

    serializer_class = ChangePasswordSerializer
    model = User

    def get_object(self, queryset=None):
        obj = self.request.user
        return obj

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                "status": "success",
                "code": status.HTTP_200_OK,
                "message": "Password updated successfully",
                "data": [],
            }

            return Response(response)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# https://github.com/CryceTruly/incomeexpensesapi/blob/master/social_auth/serializers.py
class GoogleSocialAuthView(GenericAPIView):

    serializer_class = GoogleSocialAuthSerializer

    def post(self, request):
        """
        POST with "auth_token"
        Send an idtoken as from google to get user information
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = (serializer.validated_data)["auth_token"]
        return Response(data, status=status.HTTP_200_OK)


class FacebookSocialAuthView(GenericAPIView):

    serializer_class = FacebookSocialAuthSerializer

    def post(self, request):
        """
        POST with "auth_token"
        Send an access token as from facebook to get user information
        """

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = (serializer.validated_data)["auth_token"]
        return Response(data, status=status.HTTP_200_OK)


class TwitterSocialAuthView(GenericAPIView):
    serializer_class = TwitterAuthSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class BrandsAPIView(ListCreateAPIView):
    serializer_class = BrandsSerializer

    def get_queryset(self):
        return Brand.objects.all()


class OffersAPIView(ListCreateAPIView):
    serializer_class = OffersSerializer

    def get_queryset(self):
        return Offer.objects.select_related("brand").all()


class OfferRedemptionAPIView(CreateAPIView):
    queryset = OfferRedemption.objects.all()
    serializer_class = OfferRedemptionSerializer


class PotentialUserAPIView(CreateAPIView):
    queryset = PotentialUser.objects.all()
    serializer_class = PotentialUserSerializer


class FriendsSuggestionAPIView(ListAPIView):
    """
        Show friends suggestion in order of:
            1. Mutual Friends
            2. Preferences/Interest
            3. Location
    """

    serializer_class = UserProfileSerializer
    model = serializer_class.Meta.model
    pagination_class = Limit10MaxLimit100Pagination

    def get_queryset(self):
        me = self.model.objects.get(user_id=self.request.user.id)
        my_friends = me.friends.all()
        if my_friends.exists():
            friends_of_my_friends = UserProfile.objects.none()
            for each_friend in my_friends:
                friends_of_my_friends |= each_friend.friends.all()
            profiles = friends_of_my_friends.exclude(id=me.id).distinct()
            try:
                return random.sample(list(profiles), 20)
            except ValueError:
                return profiles
        profiles = UserProfile.objects.exclude(id=me.id).filter().distinct()
        try:
            return random.sample(list(profiles), 20)
        except ValueError:
            return profiles


class InviteFriendAPIView(GenericAPIView):
    serializer_class = PotentialUserSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        potential_user = serializer.save()
        InvitationUtil.send_invitation(self.request.user, [potential_user.email])
        return Response({"email": potential_user.email, "sent": True})


class ArticleViewSet(ModelViewSet):
    serializer_class = ArticleSerializer
    queryset = Article.objects.all()
    pagination_class = Limit50MaxLimit500Pagination


class FollowRequestAPIView(GenericAPIView):
    """
        request.data
        <QueryDict: {'csrfmiddlewaretoken': ['p3f7g494N1JBnyc87TyipSynKLmbhKDcuVrPQZq9ArOV2nP1zFikRCv7DQgqWNSM'],
        'user': ['2013'], 'following_user': ['3010']}>
    """

    serializer_class = FollowRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_follow_obj = serializer.save()
        serializer.validated_data["following_user"].followers.add(
            serializer.validated_data["user"]
        )
        return Response(
            {
                "user_id": serializer.validated_data["user"].id,
                "following_user_id": serializer.validated_data["following_user"].id,
            },
            status=status.HTTP_201_CREATED,
        )
