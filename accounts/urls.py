from django.conf.urls import url
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from allauth.account import views as all_auth_views

from .views import (
    InviteView,
    AccountActivationView,
    ScheduleView,
    ScheduleDeleteView,
    RegisterView,
    LoginView,
    logout_view,
    ProfileView,
    OtherProfileView,
    searchuser,
    UserProfileView,
    UserPortfolioView,
)

app_name = "Accounts"

urlpatterns = [
    path(r"login/", LoginView.as_view(), name="login"),
    path(r"register/", RegisterView.as_view(), name="register"),
    path(r"logout/", logout_view, name="logout"),
    path(r"user-profile/<int:user_id>", UserProfileView.as_view(), name="user_profile"),
    path(
        r"user-portfolio/<int:user_id>",
        UserPortfolioView.as_view(),
        name="user_portfolio",
    ),
    path("invite/", InviteView.as_view(), name="invitation"),
    path(
        r"activate/<slug:uidb64>/<slug:token>/",
        AccountActivationView.as_view(),
        name="user_account_activation",
    ),
    url(
        r"^schedules/(?P<username>[a-zA-Z0-9]+)/$",
        ScheduleView.as_view(),
        name="schedules",
    ),
    url(
        r"^schedules/(?P<username>[a-zA-Z0-9]+)/delete/(?P<pk>\d+)$",
        ScheduleDeleteView.as_view(),
        name="delete_schedule",
    ),
    # Django auth password reset urls
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/reset_password.html",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset-done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/reset_password_sent.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_form.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/reset_password_sucess.html"
        ),
        name="password_reset_complete",
    ),
    # url(r"^password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
    #     all_auth_views.password_reset_from_key,
    #     name="account_reset_password_from_key"),
]
