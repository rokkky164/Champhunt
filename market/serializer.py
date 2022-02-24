from rest_framework import serializers
from .models import Watch
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):

    userId = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = "__all__"


class WatchSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field="username", queryset=User.objects.all()
    )

    class Meta:
        model = Watch
        fields = ("watch_name", "user")
