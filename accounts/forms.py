import re

from django import forms
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm

from .models import User, Invitation
from django.forms import formset_factory


class SignupForm(UserCreationForm):
    email = forms.EmailField(max_length=200, help_text="Required")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ReactivateEmailForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = EmailActivation.objects.email_exists(email)
        if not qs.exists():
            register_link = reverse("register")
            msg = """This email does not exist.
            Would you like to <a href="{link}">register</a>?""".format(
                link=register_link
            )
            raise forms.ValidationError(mark_safe(msg))
        return email


class UserAdminCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "email", "full_name")

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserAdminCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "full_name",
            "password",
            "is_active",
            "cash",
            "is_superuser",
        )

    def clean_password(self):
        return self.initial["password"]


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email/Mobile",
        widget=forms.TextInput(attrs={"class": "auth_form__input"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "auth_form__input"}),
    )

    def __init__(self, request, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)


class RegisterForm(forms.ModelForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={"class": "auth_form__input"}),
        required=False,
    )
    full_name = forms.CharField(
        label="Full Name",
        widget=forms.TextInput(attrs={"class": "auth_form__input"}),
        required=False,
    )
    email = forms.EmailField(
        label="Email", widget=forms.TextInput(attrs={"class": "auth_form__input"})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "auth_form__input"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "auth_form__input"}),
    )
    mobile = forms.CharField(
        label="10-digit mobile number",
        widget=forms.TextInput(attrs={"class": "auth_form__input"}),
        required=False,
    )

    class Meta:
        model = User
        fields = ("username", "full_name", "email", "mobile")

    def clean_password2(self):
        """Check that the two password entries match"""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    # def clean_username(self):
    #     username = self.cleaned_data.get("username")
    #     if not re.match(
    #         r"^[a-zA-Z0-9]+$", username
    #     ):  # Username must contain only alphanumeric characters
    #         raise forms.ValidationError(
    #             "username can contain only alphabets and numbers"
    #         )
    #     return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not re.match(
            r"^.+@.+\..+$", email
        ):  # Username must contain only alphanumeric characters
            raise forms.ValidationError("Enter a valid email")
        return email

    def save(self, commit=True):
        """Save the provided password in hashed format"""
        user = super(RegisterForm, self).save(commit=False)
        import pdb

        pdb.set_trace()
        user.set_password(self.cleaned_data["password1"])
        user.is_active = True
        if commit:
            user.save()
        return user

    # def clean_mobile(self):
    # mobile = self.cleaned_data_get('mobile')
    # if not re.match(r'^[0-9]', mobile): # Mobile must only contain numbers.  Check if we can put in a check for string length of 10 too.
    #     raise forms.ValidationError('Enter a valid mobile number')
    # return mobile


class InviteForm(forms.Form):
    email = forms.EmailField()
    name = forms.CharField(required=False)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(InviteForm, self).__init__(*args, **kwargs)

    def _get_email_field_keys(self):
        parameters = list(self.request.POST.keys())
        email_pattern = r"^invite(\d{1,10})?-email"
        email_elems = [i for i in parameters if re.match(email_pattern, i)]
        return email_elems

    def clean(self):
        cleaned_data = super().clean()
        email_elems = self._get_email_field_keys()
        for key in email_elems:
            if not self.data[key]:
                raise forms.ValidationError("Email field cannot be empty")
        return self.cleaned_data

    def save(self):
        email_elems = self._get_email_field_keys()
        from_user = self.request.user
        to_users = {}
        for key in email_elems:
            email = self.data.get(key)
            if email:
                key_elm, _ = key.split("-")
                name = self.data.get(key_elm + "-" + "name")
                to_users.update({email: name})
        Invitation.objects.create(from_user=from_user, to_users=to_users)

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")
        if not re.match(
            r"^[0-9]", mobile
        ):  # Mobile must only contain numbers.  Check if we can put in a check for string length of 10 too.
            raise forms.ValidationError("Enter a valid mobile number")
        return mobile
