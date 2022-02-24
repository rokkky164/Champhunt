from django.conf.urls import url
from django.urls import path

from .views import BrandListView, LoadUpVirtualCurrency

app_name = "VirtualCoin"


urlpatterns = [
    path("e-vouchers/", BrandListView.as_view(), name="evouchers"),
    path("load-up/", LoadUpVirtualCurrency.as_view(), name="load_up"),
]
