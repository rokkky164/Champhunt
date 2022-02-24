import threading
import decimal
import json

from django.http import JsonResponse

import channels.layers
from asgiref.sync import async_to_sync

from .models import Transaction


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def UpdateUserCashView(request):
    user = request.user
    transaction = Transaction.objects.filter(user=user).latest("id")
    trade_amount = transaction.num_stocks * transaction.orderprice
    cash_available_for_user = user.cash - trade_amount
    thread = threading.Thread(
        target=UpdateUserCash, args=[user, cash_available_for_user]
    )
    thread.setDaemon(True)
    thread.start()
    return JsonResponse({"user_id": user.id})


def UpdateUserCash(user, cash_available_for_user):
    user.cash = cash_available_for_user
    user.save()
    layer = channels.layers.get_channel_layer()
    async_to_sync(layer.group_send)(
        f"user_{user.id}",
        {
            "type": "update_user_cash_on_topnavbar",
            "data": json.dumps(
                {"cash_available_for_user": user.cash, "user_id": user.id},
                cls=DecimalEncoder,
            ),
        },
    )
