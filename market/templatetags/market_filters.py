import json

from django import template
from rest_framework import serializers


register = template.Library()


class MessageSerializer(serializers.Serializer):
    level_tag = serializers.CharField()
    message = serializers.CharField()
    tags = serializers.CharField()


@register.filter
def message_to_json(messages):
    messages_serialized = MessageSerializer(messages, many=True)
    return json.dumps(messages_serialized.data)


@register.filter
def get_badge(order_status):
    badge_to_order_mapping = {
        "Placed": "badge badge-pill badge-dark",
        "Pending": "badge badge-pill badge-secondary",
        "Cancelled": "badge badge-pill badge-warning",
        "Failed": "badge badge-pill badge-danger",
        "Completed": "badge badge-pill badge-success",
        "Order Matched": "badge badge-pill badge-info",
    }
    return badge_to_order_mapping[order_status]
