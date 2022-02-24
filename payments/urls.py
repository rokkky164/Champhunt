from django.conf.urls import url
from django.urls import path

from .views import CheckoutView, CallBackView, CheckPaymentStatus

app_name = "Payments"


urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("callback/", CallBackView.as_view(), name="callback"),
    path("payment-status/", CheckPaymentStatus.as_view(), name="payment_status"),
]
