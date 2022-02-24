from rest_framework import serializers
from market.models import Company, CompanyCMPRecord


class CompanyCMPRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyCMPRecord
        fields = ("company", "cmp", "event")


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
