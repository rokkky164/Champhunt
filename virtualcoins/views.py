import razorpay

from django.shortcuts import render, redirect, get_object_or_404

from django.views.generic import TemplateView, FormView
from django.conf import settings

from WallStreet.mixins import LoginRequiredMixin
from payments.models import PaymentTxn
from accounts.models import User

from django.http import HttpResponseRedirect, HttpResponse, JsonResponse

from .models import Brand
from .forms import LoadUpVirtualCurrencyForm


class BrandListView(TemplateView):
    template_name = "virtualcoins/brand_list.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response({"brand_list": Brand.objects.all()})


class LoadUpVirtualCurrency(FormView):
    form_class = LoadUpVirtualCurrencyForm
    template_name = "virtualcoins/load_up_currency.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        context = self.get_context_data(form=form)
        context.update(
            {
                "razorpay": Brand.objects.get(name="Razorpay"),
                "paypal": Brand.objects.get(name="Paypal"),
            }
        )
        return self.render_to_response(context=context)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        context = self.get_context_data(form=form)
        if form.is_valid():
            username = request.user.username
            user = get_object_or_404(User, username=username)
            txn_data = {
                "user": user,
                "amount": form.cleaned_data.get("amount"),
                "virtual_coins": form.cleaned_data.get("virtual_coins"),
                "bonus_code": form.cleaned_data.get("bonus_code"),
                "payment_brand": form.cleaned_data.get("payment_brand"),
            }
            transaction = self._create_txn(txn_data)
            razorpay_data = {
                "amount": txn_data["amount"] * 100,
                "currency": "INR",  # txn_data['currency']
                "receipt": str(transaction.payment_id),
            }
            client = razorpay.Client(
                auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
            )
            razorpay_response = client.order.create(data=razorpay_data)
            transaction.razorpay_response = razorpay_response
            transaction.save()
            context.update(
                {
                    "payment": True,
                    "razorpay_response": razorpay_response,
                    "client_id": settings.RAZOR_KEY_ID,
                    "user": user,
                }
            )
        return self.render_to_response(context=context)

    def _create_txn(self, txn_data):
        transaction = PaymentTxn.objects.create(**txn_data)
        return transaction
