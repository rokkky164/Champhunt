import razorpay

from django.shortcuts import render
from django.views.generic import TemplateView, FormView
from django.conf import settings

from WallStreet.mixins import LoginRequiredMixin
from .models import PaymentTxn

# authorize razorpay client with API Keys.
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)


class CheckoutView(LoginRequiredMixin, TemplateView):
    payment_index_template = "payments/payment_index.html"

    def initiate_payment(self, request):
        if request.method == "GET":
            return render(request, "payments/pay.html")
        try:
            username = request.POST["username"]
            password = request.POST["password"]
            amount = int(request.POST["amount"])
            user = authenticate(request, username=username, password=password)
            if user is None:
                raise ValueError
            auth_login(request=request, user=user)
        except:
            return render(
                request,
                "payments/pay.html",
                context={"error": "Wrong Accound Details or amount"},
            )

        transaction = Transaction.objects.create(made_by=user, amount=amount)
        transaction.save()
        merchant_key = settings.PAYTM_SECRET_KEY

        params = (
            ("MID", settings.PAYTM_MERCHANT_ID),
            ("ORDER_ID", str(transaction.order_id)),
            ("CUST_ID", str(transaction.made_by.email)),
            ("TXN_AMOUNT", str(transaction.amount)),
            ("CHANNEL_ID", settings.PAYTM_CHANNEL_ID),
            ("WEBSITE", settings.PAYTM_WEBSITE),
            # ('EMAIL', request.user.email),
            # ('MOBILE_N0', '9911223388'),
            ("INDUSTRY_TYPE_ID", settings.PAYTM_INDUSTRY_TYPE_ID),
            ("CALLBACK_URL", "http://127.0.0.1:8000/callback/"),
            # ('PAYMENT_MODE_ONLY', 'NO'),
        )

        paytm_params = dict(params)
        checksum = generate_checksum(paytm_params, merchant_key)

        transaction.checksum = checksum
        transaction.save()

        paytm_params["CHECKSUMHASH"] = checksum
        print("SENT: ", checksum)
        return render(request, "payments/redirect.html", context=paytm_params)

    def get(self, request, *args, **kwargs):
        context_data = self.get_context_data()
        return self.render_to_response(context_data)

    def post(self, request, *args, **kwargs):
        pass

    @staticmethod
    def _create_razorpay_order(amount, currency):
        # Create a Razorpay Order
        razorpay_order = razorpay_client.order.create(
            dict(amount=amount, currency=currency, payment_capture="0")
        )
        return razorpay_order


class CallBackView(TemplateView):
    def callback(self, request):
        if request.method == "POST":
            received_data = dict(request.POST)
            paytm_params = {}
            paytm_checksum = received_data["CHECKSUMHASH"][0]
            for key, value in received_data.items():
                if key == "CHECKSUMHASH":
                    paytm_checksum = value[0]
                else:
                    paytm_params[key] = str(value[0])
            # Verify checksum
            is_valid_checksum = verify_checksum(
                paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum)
            )
            if is_valid_checksum:
                received_data["message"] = "Checksum Matched"
            else:
                received_data["message"] = "Checksum Mismatched"
                return render(request, "payments/callback.html", context=received_data)
            return render(request, "payments/callback.html", context=received_data)

    def post(self, request, *args, **kwargs):
        pass


class CheckPaymentStatus(TemplateView):
    def post(self, request, *args, **kwargs):
        response = request.POST
        params_dict = {
            "razorpay_order_id": response["razorpay_order_id"],
            "razorpay_payment_id": response["razorpay_payment_id"],
            "razorpay_signature": response["razorpay_signature"],
        }
        client = razorpay.Client(
            auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
        )
        try:
            status = client.utility.verify_payment_signature(params_dict)
            transaction = PaymentTxn.objects.get(
                razorpay_order_id=response["razorpay_order_id"]
            )
            transaction.status = "Done"
            transaction.save()
            return render(request, "payments/payment_success.html", context=params_dict)
        except:
            return render(request, "payments/payment_failed.html", context=params_dict)
