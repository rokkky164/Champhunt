from django.db import models

from django.core.validators import FileExtensionValidator
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from rest_api.models import AbstractDateTimeModel


BRAND_CHOICES = (
    ("Entertainment Subscriptions", "Entertainment Subscriptions"),
    ("Apparel & Accessories", "Apparel & Accessories"),
    ("Food & Beverage", "Food & Beverage"),
    ("Mobile & Electronics", "Mobile & Electronics"),
    ("Health & Wellness", "Health & Wellness"),
    ("Magazines Subscriptions", "Magazines Subscriptions"),
    ("Cabs & Travels", "Cabs & Travels"),
    ("Sports", "Sports"),
)

OFFER_TYPES = (("", ""),)


class Brand(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=100, choices=BRAND_CHOICES, blank=True, null=True
    )
    logo = models.ImageField(
        upload_to="brandlogos/%Y/%m/%d",
        blank=True,
        validators=[FileExtensionValidator(["jpeg", "jpg", "svg"])],
    )

    def __str__(self):
        return self.name


class Offer(models.Model):
    name = models.CharField(max_length=255)
    validity = models.DateTimeField()
    offer_type = models.CharField(
        max_length=100, choices=OFFER_TYPES, blank=True, null=True
    )
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    crickcoins_required = models.IntegerField(default=1000)
    total_redeemable_units = models.IntegerField(default=999999)
    is_redeemable = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}--{self.validity.strftime('%Y/%m/%d')}"


class OfferRedemption(AbstractDateTimeModel):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    userprofile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.offer.name}--{self.userprofile.user.email}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.offer.total_redeemable_units > 0:
                self.offer.total_redeemable_units -= 1
            if self.offer.total_redeemable_units <= 0:
                self.offer.is_redeemable = False
            self.offer.save()
            crickcoins_used = self.offer.crickcoins_required
            runs_used = 100 * crickcoins_used  # 100 runs => crickcoins
            self.userprofile.runs -= runs_used
            self.userprofile.save()
        super().save(*args, **kwargs)
