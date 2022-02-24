from django.conf.urls import url
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    RegisterAPIView,
    LoginView,
    PotentialUserAPIView,
    GoogleSocialAuthView,
    FacebookSocialAuthView,
    TwitterSocialAuthView,
    UserReadOnlyViewSet,
    UserProfileViewSet,
    LoggedInUserProfileAPIView,
    PitchReadOnlyViewSet,
    PitchViewSet,
    UserPitchScoreViewSet,
    ReportPitchViewSet,
    OfferRedemptionAPIView,
    SearchPitchesAPIView,
    SearchUsersAPIView,
    LogoutAPIView,
    ResetPasswordAPIView,
    PasswordResetConfirmAPIView,
    ChangePasswordView,
    BrandsAPIView,
    OffersAPIView,
    FriendsSuggestionAPIView,
    SearchAPIView,
    PitchCommentViewSet,
    PitchCommentReadOnlyViewSet,
    SharePitchViewSet,
    NotificationsReadOnlyViewSet,
    InviteFriendAPIView,
    FollowRequestAPIView,
)

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"users", UserReadOnlyViewSet, basename="user")
router.register(r"user-profile", UserProfileViewSet, basename="user_profile")
router.register(r"pitches", PitchReadOnlyViewSet, basename="pitch")
router.register(r"submit-pitch", PitchViewSet, basename="submit_pitch")
router.register(r"user-score-pitch", UserPitchScoreViewSet, basename="pitch_score")
router.register(r"report-pitch", ReportPitchViewSet, basename="report_pitch")
router.register(
    r"get-pitch-comments", PitchCommentReadOnlyViewSet, basename="get_pitch_comments"
)
router.register(r"submit-comment", PitchCommentViewSet, basename="submit_comment")
router.register(r"share-pitch", SharePitchViewSet, basename="share_pitch")
router.register(
    r"get-notifications", NotificationsReadOnlyViewSet, basename="get_notifications"
)

app_name = "RestAPI"


urlpatterns = [
    # jwt apis
    path("jwt-refresh-token/", TokenRefreshView.as_view(), name="token_refresh"),
    path("jwt-verify-token/", TokenVerifyView.as_view(), name="token_verify"),
    ##
    url(r"^register/", RegisterAPIView.as_view(), name="register"),
    url(r"^login/", LoginView.as_view(), name="login"),
    url(r"^login-google/", GoogleSocialAuthView.as_view(), name="login_google"),
    url(r"^login-facebook/", FacebookSocialAuthView.as_view(), name="login_facebook"),
    url(r"^login-twitter/", TwitterSocialAuthView.as_view(), name="login_twitter"),
    url(r"^logout/", LogoutAPIView.as_view(), name="logout"),
    url(r"^change-password/", ChangePasswordView.as_view(), name="change_pwd"),
    url(r"^reset-password/", ResetPasswordAPIView.as_view(), name="reset_password"),
    url(
        r"^reset-password-confirm/",
        ResetPasswordAPIView.as_view(),
        name="reset_password_confirm",
    ),
    # url(r"^create-profile/", UserProfileAPIView.as_view(), name="create_profile"),
    url(r"^search-pitches/", SearchPitchesAPIView.as_view(), name="search_pithces"),
    url(r"^search-users/", SearchUsersAPIView.as_view(), name="search_users"),
    url(r"^search/", SearchAPIView.as_view(), name="search"),
    url(r"^brands/", BrandsAPIView.as_view(), name="brands"),
    url(r"^offers/", OffersAPIView.as_view(), name="offers"),
    url(r"^redeem/", OfferRedemptionAPIView.as_view(), name="redeem_coupons"),
    url(r"^potential-user/", PotentialUserAPIView.as_view(), name="potential_user"),
    url(
        r"^logged-in-profile/",
        LoggedInUserProfileAPIView.as_view(),
        name="logged_in_profile",
    ),
    url(
        r"^friends-suggestion/",
        FriendsSuggestionAPIView.as_view(),
        name="friends_suggestion",
    ),
    url(r"^invite-friends/", InviteFriendAPIView.as_view(), name="invite_friends"),
    url(r"^follow/", FollowRequestAPIView.as_view(), name="follow"),
]

urlpatterns += router.urls
