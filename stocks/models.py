from django.db import models
from django.db.models.signals import post_save

from market.models import Company, CompanyCMPRecord

# This is a test comment
class StocksDatabase(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    pointer = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ("company", "pointer")
        ordering = ["company", "pointer"]

    def __str__(self):
        return self.company.name + " - " + str(self.pointer) + " - " + str(self.price)


class StocksDatabasePointerManager(models.Manager):
    def get_pointer(self):
        return self.get_queryset().all().first()


class StocksDatabasePointer(models.Model):
    pointer = models.IntegerField(default=0)

    objects = StocksDatabasePointerManager()

    def __str__(self):
        return str(self.pointer)

    def increment_pointer(self):
        self.pointer += 1
        self.save()
        return self.pointer


def post_save_stocks_database_pointer_receiver(
    sender, instance, created, *args, **kwargs
):
    if not created:
        for company in Company.objects.all():
            new_price = StocksDatabase.objects.get(
                company=company, pointer=instance.pointer
            ).price
            company.update_cmp(new_price)
            CompanyCMPRecord.objects.create(company=company, cmp=new_price)


post_save.connect(
    post_save_stocks_database_pointer_receiver, sender=StocksDatabasePointer
)
