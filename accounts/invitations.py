from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse_lazy


class InvitationUtil(object):
    ACCEPTATION_URL = reverse_lazy("accounts:register")

    @staticmethod
    def send_mail(
        subject=None,
        template_name="",
        context={},
        from_email="",
        to_emails=[],
        user_referral_code=None,
    ):
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, to_emails)
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    @staticmethod
    def send_invitation(user, to_emails, user_referral_code=None):
        InvitationUtil.send_mail(
            subject="{{username}} invited you to Cricket Stock Market".format(
                username=user.username
            ),
            template_name="accounts/email_invitation.html",
            context={
                "user": user,
                "invited_name": "",
                "invitation_url": "",
                "currency": "INR",  # default
            },
            from_email=user.email,
            to_emails=to_emails,
            user_referral_code=user_referral_code,
        )

    def send_invitation_accepted(self, user, invitation):
        self.send_mail(
            subject="{{username}} invited you to Cricket Stock Market".format(
                username=user.username
            ),
            template_name="accounts/email_accepted_invitation.html",
            context={"user": user, "invited_name": "",},
            from_email=settings.EMAIL_HOST_USER,
            to_emails=[user.email],
        )
