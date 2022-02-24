import facebook
import twitter
import os
from PIL import Image

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import smart_bytes, force_text
from django.utils.encoding import force_bytes, force_text

from rest_framework import serializers

from google.auth.transport import requests
from google.oauth2 import id_token

from accounts.models import FriendRequest


class FriendRequestMixin(object):
    def send_friend_request(self, from_user, to_user):
        """
        return:
            status, model_instance
        """
        friend_request, created = FriendRequest.objects.get_or_create(
            {"from_user": from_user, "to_user": to_user}
        )
        if created:
            return "sent", friend_request
        else:
            return "already_sent", friend_request

    def accept_friend_request(self, friend_request_id, to_user):
        """
        return:
            status
        """
        friend_request = FriendRequest.objects.get(id=friend_request_id)
        if friend_request.to_user == to_user:
            friend_request.from_user.friends.add(friend_request.to_user)
            friend_request.to_user.friends.add(friend_request.from_user)
            friend_request.status = FriendRequest.ACCEPTED
            friend_request.save()
            return "done"
        return "pending"

    def decline_friend_request(self, friend_request_id):
        friend_request = FriendRequest.objects.get(id=friend_request_id)
        friend_request.status = FriendRequest.DECLINED
        friend_request.save()
        return "done"

    def unfriend(self, friend_request_id):
        friend_request.status = FriendRequest.UNFRIENDED
        friend_request.save()


class MailMixin(object):
    def send_email_for_account_activation(self, request, user):

        current_site = get_current_site(request)
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

    def send_email_for_reset_password(self, request, user):

        current_site = get_current_site(request)
        mail_subject = "Reset your password"

        message = render_to_string(
            "accounts/password_reset_email.html",
            {
                "user": user,
                "domain": current_site.domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": account_activation_token.make_token(user),
            },
        )
        to_email = user.email
        email = EmailMessage(mail_subject, message, to=[to_email])
        email.send()


class Facebook(object):
    """
    Facebook class to fetch the user info and return it
    """

    @staticmethod
    def validate(auth_token):
        """
        validate method Queries the facebook GraphAPI to fetch the user info
        """
        try:
            graph = facebook.GraphAPI(access_token=auth_token)
            profile = graph.request("/me?fields=name,email")
            return profile
        except:
            return "The token is invalid or expired."


class Google(object):
    """Google class to fetch the user info and return it"""

    @staticmethod
    def validate(auth_token):
        """
        validate method Queries the Google oAUTH2 api to fetch the user info
        """
        try:
            idinfo = id_token.verify_oauth2_token(auth_token, requests.Request())

            if "accounts.google.com" in idinfo["iss"]:
                return idinfo

        except:
            return "The token is either invalid or has expired"


class TwitterAuthTokenVerification(object):
    """
    class to decode user access_token and user access_token_secret
    tokens will combine the user access_token and access_token_secret
    separated by space
    """

    @staticmethod
    def validate_twitter_auth_tokens(access_token_key, access_token_secret):
        """
        validate_twitter_auth_tokens methods returns a twitter
        user profile info
        """

        consumer_api_key = os.environ.get("TWITTER_API_KEY")
        consumer_api_secret_key = os.environ.get("TWITTER_CONSUMER_SECRET")

        try:
            api = twitter.Api(
                consumer_key=consumer_api_key,
                consumer_secret=consumer_api_secret_key,
                access_token_key=access_token_key,
                access_token_secret=access_token_secret,
            )

            user_profile_info = api.VerifyCredentials(include_email=True)
            return user_profile_info.__dict__

        except Exception as identifier:

            raise serializers.ValidationError(
                {"tokens": ["The tokens are invalid or expired"]}
            )


class FilterAdultContent(object):
    def get_skin_ratio(self, im):
        """
         for skin ratio > 50 %
         remove the image
        """
        im = Image.open(im.file)
        im = im.crop(
            (
                int(im.size[0] * 0.2),
                int(im.size[1] * 0.2),
                im.size[0] - int(im.size[0] * 0.2),
                im.size[1] - int(im.size[1] * 0.2),
            )
        )
        skin = sum(
            [
                count
                for count, rgb in im.getcolors(im.size[0] * im.size[1])
                if rgb[0] > 60
                and rgb[1] < (rgb[0] * 0.85)
                and rgb[2] < (rgb[0] * 0.7)
                and rgb[1] > (rgb[0] * 0.4)
                and rgb[2] > (rgb[0] * 0.2)
            ]
        )
        return float(skin) / float(im.size[0] * im.size[1])
