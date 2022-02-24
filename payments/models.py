import uuid

from django.db import models
from jsonfield import JSONField
from collections import OrderedDict

STATUS_CHOICES = (
    ("Pending", "Pending"),
    ("Done", "Done"),
)


class PaymentTxn(models.Model):
    payment_id = models.CharField(max_length=255, default=uuid.uuid4)
    user = models.ForeignKey(
        "accounts.User", related_name="payment_users", on_delete=models.CASCADE
    )
    amount = models.FloatField()
    virtual_coins = models.IntegerField(blank=True, null=True)
    bonus_code = models.CharField(max_length=255, blank=True, null=True)
    payment_brand = models.CharField(max_length=255)
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    razorpay_response = JSONField(
        load_kwargs={"object_pairs_hook": OrderedDict}, default=OrderedDict()
    )

    def __str__(self):
        return f"{self.user.username}--{self.payment_id}"
