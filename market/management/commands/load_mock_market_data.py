import random
import json

from time import sleep

from django.utils import timezone
from django.core.management import BaseCommand
from django.db import IntegrityError
from dateutil.relativedelta import relativedelta

from accounts.models import User

from market.models import (
    Company,
    CompanyCMPRecord,
    CMP_CHANGE_REASONS,
    ORDER_STATUS,
    Order,
    Watch,
)
from market.management.commands.mockplayerdata import COMPANIES


class Command(BaseCommand):
    user = User.objects.get(email="hansdah.roshan@gmail.com")
    companies = Company.objects.all()

    def handle(self, *args, **options):
        self.load_company(COMPANIES)
        self.loadup_company_cmp_records()
        # self.load_order_data()
        # self.load_watchlists()

    def load_company(self, companies):
        for company_data in companies:
            try:
                Company.objects.create(**company_data)
            except IntegrityError:
                print("Company object with the given code already exists")

    def loadup_company_cmp_records(self):
        companies = list(Company.objects.all())
        iterator = 100
        while iterator > 0:
            iterator -= 1
            print(iterator)
            cmp = float(random.choice(range(10, 251)))
            today = timezone.now()
            days = range(200)
            random_day = random.choice(days)
            random_hour = random.choice(range(24))
            timestamp = (
                today
                - relativedelta(days=random_day)
                - relativedelta(hours=random_hour)
                - relativedelta(minutes=random.choice(range(60)))
            )
            company = random.choice(companies)
            cmp_data = {
                "company_id": company.id,
                "cmp": cmp,
                "event": random.choice(list(dict(CMP_CHANGE_REASONS).keys())),
                "timestamp": today,
            }
            CompanyCMPRecord.objects.create(**cmp_data)

    def load_order_data(self):
        for company in self.companies[:10]:
            order_data = {
                "user": self.user,
                "company": company,
                "num_stocks": random.choice([10, 125]),
                "execution_price": random.choice([20, 200]),
                "status": random.choice(list(dict(ORDER_STATUS).keys())),
            }
            order = Order.objects.create(**order_data)
            order.brokerage = (
                order_data["execution_price"] * 0.04
            )  # 4% of the execution price
            order.save()

    def load_watchlists(self):
        user = User.objects.get(email="hansdah.roshan@gmail.com")
        watchlist_names = ["My Stocks", "Top performing", "Batsmen"]
        for watch_name in watchlist_names:
            watchlist_data = {"user": self.user, "watch_name": watch_name}
            watch = Watch.objects.create(**watchlist_data)
            random_no = random.choice(range(len(self.companies)))
            for company in self.companies[:random_no]:
                watch.stocks.add(company.id)

    def test_out_websocket_conn(self):
        for i in range(10):
            sleep(3.5)
            data = json.dumps(
                {
                    "name": random.choice(["EOM", "MSD", "HAP", "SUR", "KEP"]),
                    "value": random.choice(range(500)),
                }
            )
            ws.send(data)
