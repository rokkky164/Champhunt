import re
import base64
import uuid
import six

from datetime import datetime

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.views.generic import (
    ListView,
    DetailView,
    FormView,
    CreateView,
    DeleteView,
    View,
    TemplateView,
)
from django.contrib.auth.tokens import default_token_generator
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.db.models import Q
from django.contrib.auth import views as auth_views
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from market.models import (
    InvestmentRecord,
    TransactionScheduler,
    Company,
    Buystage,
    Sellstage,
    PlayerValuations,
    CurrentMatch,
    CancelledOrders,
    UpcomingMatches,
)

from WallStreet.mixins import (
    AnonymousRequiredMixin,
    RequestFormAttachMixin,
    NextUrlMixin,
    LoginRequiredMixin,
    CountNewsMixin,
)

from .forms import LoginForm, RegisterForm, InviteForm

from .invitations import InvitationUtil

from .models import User

START_TIME = timezone.make_aware(getattr(settings, "START_TIME"))
STOP_TIME = timezone.make_aware(getattr(settings, "STOP_TIME"))
BOTTOMLINE_CASH = getattr(settings, "BOTTOMLINE_CASH", 1000)
MAX_LOAN_ISSUE = getattr(settings, "MAX_LOAN_ISSUE", 1000)


@login_required
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk)
            + six.text_type(timestamp)
            + six.text_type(user.is_active)
        )


account_activation_token = TokenGenerator()


class LeaderBoardView(CountNewsMixin, View):
    template_name = "accounts/leaderboard.html"

    def get(self, request, *args, **kwargs):
        data = []
        user_qs = get_user_model().objects.filter(is_superuser=False)
        for user in user_qs:
            net_worth = InvestmentRecord.objects.calculate_net_worth(user)
            data.append((user.username, user.get_full_name(), net_worth,))
        data = sorted(data, key=lambda d: (-d[2], d[3]))

        # Obtain data and rank of current user
        current_user_data = []
        rank_count = 1
        for user_data in data:
            if user_data[0] == self.request.user.username:
                current_user_data.append((user_data, rank_count))
            rank_count += 1
        return render(
            request,
            "accounts/leaderboard.html",
            {"data": data, "current_user": current_user_data},
        )


class AccountActivationView(View):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return HttpResponse(
                "Thank you for your email confirmation. Now you can login your account."
            )
        else:
            return HttpResponse("Activation link is invalid!")


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    success_url = "/market/overview/"

    def get_context_data(self, *args, **kwargs):
        context = super(LoginView, self).get_context_data(*args, **kwargs)
        context["heading"] = "Login"
        context["button_text"] = "Sign In"
        context["unauthorized"] = True
        return context


class RegisterView(AnonymousRequiredMixin, CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = "accounts/login/"

    def get_context_data(self, *args, **kwargs):
        context = super(RegisterView, self).get_context_data(*args, **kwargs)
        context["unauthorized"] = True
        return context

    def form_valid(self, form):
        super(RegisterView, self).form_valid(form)
        user = form.save()
        self.send_email_for_account_activation(user)
        messages.success(
            self.request, "Verification link sent! Please check your email."
        )
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.success(self.request, "form invalid")
        return redirect("/")

    def send_email_for_account_activation(self, user):

        current_site = get_current_site(self.request)
        mail_subject = "Activate your cricktrade account."

        message = render_to_string(
            "accounts/acc_active_email.html",
            {
                "user": user,
                "domain": current_site.domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": account_activation_token.make_token(user),
                "heading": "Sign Up",
            },
        )
        to_email = user.email
        email = EmailMessage(mail_subject, message, to=[to_email])
        email.send()


class ProfileView(LoginRequiredMixin, CountNewsMixin, DetailView):
    template_name = "accounts/profile.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.username != kwargs.get("username"):
            return redirect("/")
        return super(ProfileView, self).dispatch(request, *args, **kwargs)

    def get_object(self, *args, **kwargs):
        username = self.kwargs.get("username")
        instance = get_user_model().objects.filter(username=username).first()
        if instance is None:
            return Http404("User not found")
        return instance

    def get_context_data(self, *args, **kwargs):
        context = super(ProfileView, self).get_context_data(*args, **kwargs)
        hometeam = ""
        awayteam = ""
        match = CurrentMatch.objects.all()
        for m in match:
            hometeam = m.home_team
            awayteam = m.away_team
        context["company_list"] = PlayerValuations.objects.filter(
            Q(team__icontains=hometeam) | Q(team__icontains=awayteam)
        )
        context["net_worth"] = InvestmentRecord.objects.calculate_net_worth(
            self.request.user
        )
        context["pending_buy"] = Buystage.objects.filter(user=self.request.user)
        context["pending_sell"] = Sellstage.objects.filter(user=self.request.user)
        context["cancelled"] = CancelledOrders.objects.filter(user=self.request.user)
        context["upcomingmatches"] = UpcomingMatches.objects.all()
        qs = InvestmentRecord.objects.filter(user=self.request.user, stocks__gt=0)
        if qs.count() >= 1:
            context["investments"] = qs
        return context


class OtherProfileView(LoginRequiredMixin, CountNewsMixin, View):
    template_name = "accounts/other_user_profile.html"

    def get(self, request, *args, **kwargs):
        username = kwargs.get("username")
        user = get_user_model().objects.get(username=username)
        investments = InvestmentRecord.objects.filter(user=user, stocks__gt=0)
        context = {
            "object": user,
            "company_list": PlayerValuations.objects.filter(
                Q(team__icontains=hometeam) | Q(team__icontains=awayteam)
            ),
            "investments": investments,
        }
        return render(request, "accounts/other_user_profile.html", context)


def searchuser(request):
    query = ""
    query = request.GET["query"].strip()
    allUsers = (
        get_user_model()
        .objects.all()
        .filter(Q(username__icontains=query) | Q(name__icontains=query))
    )
    context = {"allUsers": allUsers, "query": query}
    return render(request, "accounts/searchuser.html", context)


class ScheduleView(LoginRequiredMixin, CountNewsMixin, ListView):
    template_name = "accounts/schedules.html"

    def get_queryset(self):
        return TransactionScheduler.objects.get_by_user(self.request.user)


class ScheduleDeleteView(LoginRequiredMixin, DeleteView):
    def get_object(self, **kwargs):
        print(self.kwargs)
        obj = TransactionScheduler.objects.get(pk=self.kwargs.get("pk"))
        return obj

    def get_success_url(self):
        return reverse_lazy(
            "accounts:schedules", kwargs={"username": self.request.user.username}
        )


class InviteView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/invite.html"
    form_class = InviteForm

    def save_additional_emails(self, request):
        for name in list(request.POST.keys()):
            email_pattern = r"^invite(\d{1,10})-email"
            name_pattern = r"^invite(\d{1,10})-name"
            result = re.match(pattern, name)
            # if result:

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        form = InviteForm(request=request, data=request.POST, prefix="invite")

        if form.is_valid():
            invitation = form.save()
            context = self.get_context_data()
            context.update({"form": form, "invitation": invitation})
            if not invitation.from_user.referral_code:
                self.request.user.create_referral_code()
            InvitationUtil.send_invitation(
                self.request.user,
                list(invitation.to_users.keys()),
                user_referral_code=invitation.from_user.referral_code,
            )
            messages.success(request, "Invitation has been sent")
        else:
            messages.error(request, form.error.get("email"))
        return self.render_to_response(self.get_context_data(**kwargs))


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/user_profile.html"

    def get(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, pk=user_id)
        return self.render_to_response({"user": user,})


class UserPortfolioView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/user_portfolio.html"

    def get(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, pk=user_id)
        return self.render_to_response({"user": user,})
