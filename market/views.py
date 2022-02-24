import operator

from datetime import datetime, timedelta
from django.db.models.aggregates import Max, Min
from django.utils.timezone import make_aware
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.generic import ListView
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from django.conf import settings
from django.urls import reverse
from django.db.models import Q
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.contrib.messages import api as message_api
from django.views.generic.edit import CreateView
from django.utils.safestring import mark_safe
from django.db.models import Sum, Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from accounts.models import User
from .models import (
    Company,
    CompanyValuations,
    InvestmentRecord,
    Transaction,
    CompanyCMPRecord,
    News,
    UserNews,
    TransactionScheduler,
    Buystage,
    Sellstage,
    CompletedOrders,
    CurrentMatch,
    Match,
    PlayerValuations,
    AllMatches,
    UpcomingMatches,
    Order,
    Watch,
    BallbyBall,
)
from .forms import (
    CompanyChangeForm,
    ScoreCardForm,
    MatchCreationForm,
    OrderBookForm,
    StockSearchForm,
    OrderCreationForm,
    SearchNavBarForm,
    TransactStockForm,
)
from .serializer import WatchSerializer
from WallStreet.mixins import LoginRequiredMixin, AdminRequiredMixin, CountNewsMixin
from stocks.models import StocksDatabasePointer

import psycopg2

# For Player Data parsing
import requests
from bs4 import BeautifulSoup
import dateparser
import time
from datetime import datetime

from django.http.response import JsonResponse
from django.core import serializers
from django.views.generic.edit import FormView

from .mixins import BaseChartAPIView


dbHost = settings.DATABASES["default"]["HOST"]
dbUsername = settings.DATABASES["default"]["USER"]
dbPassword = settings.DATABASES["default"]["PASSWORD"]
dbName = settings.DATABASES["default"]["NAME"]
dbPort = settings.DATABASES["default"]["PORT"]


START_TIME = timezone.make_aware(getattr(settings, "START_TIME"))
STOP_TIME = timezone.make_aware(getattr(settings, "STOP_TIME"))


@login_required
def deduct_tax(request):
    if request.user.is_superuser:
        for user in User.objects.all():
            tax = user.cash * Decimal(0.4)
            user.cash -= tax
            user.save()
        return HttpResponse("success")
    return redirect("/")


class UpdateMarketView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # update cmp
        StocksDatabasePointer.objects.get_pointer().increment_pointer()

        # scheduler
        schedule_qs = TransactionScheduler.objects.all()
        for query in schedule_qs:
            if query.perform_transaction(query.company.cmp):
                TransactionScheduler.objects.get(pk=query.pk).delete()

        return HttpResponse("cmp updated")


def getMarketData(request):

    hometeam = ""
    awayteam = ""
    match = CurrentMatch.objects.all()
    for m in match:
        hometeam = m.home_team
        awayteam = m.away_team

    losers = (
        CompanyValuations.objects.all().filter(cmp__gt=0).order_by("current_form")[:7]
    )
    gainers = (
        CompanyValuations.objects.all().filter(cmp__gt=0).order_by("-current_form")[:7]
    )
    players = CompanyValuations.objects.filter(Q(team=hometeam) | Q(team=awayteam))

    losersData = serializers.serialize("json", losers)
    gainersData = serializers.serialize("json", gainers)
    playerData = serializers.serialize("json", players)

    return JsonResponse(
        {"losers": losersData, "gainers": gainersData, "players": playerData}
    )


def getPortfolio(request):
    holdings = InvestmentRecord.objects.filter(user=request.user).filter(
        stocks__gt=0
    )  # added .filter(stocks__gt=0) to get only those entries for which a user has non-zero stocks
    data = serializers.serialize("json", holdings)
    return HttpResponse(data, content_type="application/json")


def searchPlayer(request, player):

    allCompanies = Company.objects.all().filter(name__icontains=player)

    data = serializers.serialize("json", allCompanies)
    return HttpResponse(data, content_type="application/json")


def getAllPlayers(request):
    players = CompanyValuations.objects.all()
    data = serializers.serialize("json", players)
    return HttpResponse(data, content_type="application/json")


class MarketOverview(LoginRequiredMixin, TemplateView):
    template_name = "market/market_index.html"

    def get_context_data(self, *args, **kwargs):
        context = super(MarketOverview, self).get_context_data(*args, **kwargs)
        context["players"] = Company.objects.all()
        context["user"] = self.request.user
        return context


class MarketPlaceOrder(LoginRequiredMixin, TemplateView):
    template_name = "market/place_order.html"


class CompanyAdminCompanyUpdateView(AdminRequiredMixin, CountNewsMixin, View):
    def get(self, request, *args, **kwargs):
        company = Company.objects.get(code=kwargs.get("code"))
        return render(
            request,
            "market/admin_company_change.html",
            {
                "object": company,
                "company_list": Company.objects.all(),
                "form": CompanyChangeForm(),
            },
        )

    def post(self, request, *args, **kwargs):
        company = Company.objects.get(code=kwargs.get("code"))
        price = request.POST.get("price")
        old_price = company.cmp
        company.cmp = Decimal(int(price))
        company.save()
        company.calculate_change(old_price)
        url = reverse("market:admin", kwargs={"code": company.code})
        return HttpResponseRedirect(url)


class CompanyTransactionView(
    LoginRequiredMixin, CountNewsMixin, View
):  # This is what is causing Investment Record entry to be created every time the user visits a stock's profile page
    def get(self, request, *args, **kwargs):
        company_code = kwargs.get("code")
        company = Company.objects.get(code=company_code)
        # I tried turning this method to InvestmentRecord.objects.get instead of get_or_create, but apparently, the players' profile pages are getting created based on the InvestmentRecordObject being created here.
        obj, _ = InvestmentRecord.objects.get_or_create(
            user=request.user, company=company
        )
        stocks_owned = obj.stocks
        if company.cmp > 0:
            percentage_change = round(
                (round(company.change, 2) / round(company.cmp - company.change, 2))
                * 100,
                2,
            )
        else:
            percentage_change = 0
        # percentage_change = round((company.change/(company.cmp - company.change))*100,2)
        hometeam = ""
        awayteam = ""
        match = CurrentMatch.objects.all()
        for m in match:
            hometeam = m.home_team
            awayteam = m.away_team
        context = {
            "object": company,
            "company_list": PlayerValuations.objects.filter(
                Q(team__icontains=hometeam) | Q(team__icontains=awayteam)
            ),
            "stocks_owned": stocks_owned,
            "purchase_modes": ["buy", "sell"],
            "percentage_change": percentage_change,
        }
        return render(request, "market/transaction_market.html", context)

    def post(self, request, *args, **kwargs):
        """This method handles any post data at this page (primarily for transaction)"""
        company = Company.objects.get(code=kwargs.get("code"))
        current_time = timezone.make_aware(datetime.now())

        if START_TIME <= current_time <= STOP_TIME:
            user = request.user
            quantity = request.POST.get("quantity")

            if quantity != "" and int(quantity) > 0:
                quantity = int(quantity)
                mode = request.POST.get("mode")
                purchase_mode = request.POST.get("p-mode")
                price = company.cmp
                # Investment object is being used only to check if the user has sufficient stock balance before trying to sell
                # When I try to use get, it shows the following error: TypeError: cannot unpack non-iterable InvestmentRecord object
                investment_obj, _ = InvestmentRecord.objects.get_or_create(
                    user=user, company=company
                )
                holding = investment_obj.stocks
                # If num_stocks for sell orders are stored as negative integers, we could aggregate num_stocks and come to the holding for a particular company - WORKS!
                """sql = "SELECT stocks as holding FROM MARKET_COMPLETEDORDERS WHERE user_id = " + str(user.id) + " AND COMPANY_ID = " + str(company.id) + " GROUP BY COMPANY_ID;"
                holding = 0
                conn = psycopg2.connect(database="wallstreet", user="postgres", password="admin", host="localhost", port="5432")
                cursor = conn.cursor()
                cursor.execute(sql)
                holdings = [row for row in cursor]
                for entry in holdings:
                    holding = entry[0]"""

                # This code is for when the num_stocks for sell orders are stored as positive integers - WORKS!
                """holding = 0
                sql = "SELECT num_stocks, mode FROM MARKET_COMPLETEDORDERS WHERE user_id = " + str(user.id) + " AND COMPANY_ID = " + str(company.id) + ";"

                conn = psycopg2.connect(database="wallstreet", user="postgres", password="admin", host="localhost", port="5432")
                cursor = conn.cursor()
                cursor.execute(sql)
                mode_and_qty = [row for row in cursor]
                for entry in mode_and_qty:
                    if entry[1] == 'BUY':
                        holding = holding + entry[0]
                    elif entry[1] == 'SELL':
                        holding = holding - entry[0]"""

                if mode == "transact":
                    if purchase_mode == "buy":
                        purchase_amount = Decimal(quantity) * price
                        brokerage = Decimal(purchase_amount) * Decimal(0.01)
                        if user.cash >= (
                            purchase_amount + brokerage
                        ):  # Checking if the user has sufficient cash balance for the transaction
                            # Checking how many stocks of the company have already been sold till now
                            count = 0
                            repos = InvestmentRecord.objects.all().filter(
                                company=company
                            )
                            for repo in repos:
                                count = count + repo.stocks

                            # Checking how many stocks of this company the user already has
                            # We have already fetched the user's stock count in the variable 'holding' on line 204. See if this loop can be removed.
                            userstockcount = 0
                            repos = InvestmentRecord.objects.all().filter(
                                company=company, user=user
                            )
                            for repo in repos:
                                userstockcount = userstockcount + repo.stocks

                            if (
                                userstockcount + quantity
                            ) < 1000:  # You can limit the number of stocks of a particular company a user is allowed to hold here.
                                # if (count + quantity) < 100000: # This can be commented out when we stop generating admin buy/sell orders automatically
                                # Assigning the created transaction to buyorder
                                _ = Transaction.objects.create(
                                    user=user,
                                    company=company,
                                    num_stocks=quantity,
                                    orderprice=price,
                                    mode=purchase_mode.upper(),
                                    status="OPEN"
                                    # user_net_worth=InvestmentRecord.objects.calculate_net_worth(user)
                                )
                                # Updating investment record - adding shares to buy escrow
                                obj, _ = InvestmentRecord.objects.get_or_create(
                                    user=request.user, company=company
                                )
                                obj.buy_escrow = obj.buy_escrow + quantity
                                obj.save()
                                print("buy escrow = " + str(obj.buy_escrow))
                                print(
                                    "User BUY order placed user="
                                    + user.username
                                    + " company="
                                    + company.name
                                    + " qty="
                                    + str(quantity)
                                )

                                messages.success(
                                    request,
                                    "BUY order for "
                                    + str(quantity)
                                    + " shares of "
                                    + company.name
                                    + " placed at "
                                    + str(price)
                                    + ". Please check your profile for its status",
                                )

                                # Subtracting cash from user's account
                                # We need an order confirmation page that shows the particulars of a user's order to him.
                                # Can we programme a cart?
                                user.escrow = user.escrow + purchase_amount + brokerage
                                user.cash = user.cash - purchase_amount - brokerage
                                user.save()

                                sellorders = Sellstage.objects.all().filter(
                                    company=company
                                )
                                if (
                                    sellorders
                                ):  # If there are user sell orders, they get priority
                                    pass
                                else:
                                    # This code below is when you want an admin sell order to be placed automatically whenever a user buy order is placed
                                    if (
                                        count + quantity
                                    ) < 100000:  # 100000 is the maximum number of stocks in the system for a company
                                        # Creating an admin sell order
                                        adminuser, _ = User.objects.get_or_create(
                                            username="admin"
                                        )  # Username admin to sell all stocks
                                        _ = Transaction.objects.create(
                                            user=adminuser,
                                            company=company,
                                            num_stocks=quantity,
                                            orderprice=price,
                                            mode="SELL",
                                        )
                                        obj, _ = InvestmentRecord.objects.get_or_create(
                                            user=adminuser, company=company
                                        )
                                        obj.sell_escrow = obj.sell_escrow + quantity
                                        obj.stocks = obj.stocks - quantity
                                        obj.save()
                                        print(
                                            "Admin SELL order placed user="
                                            + adminuser.username
                                            + " company="
                                            + company.name
                                            + " qty="
                                            + str(quantity)
                                        )
                            else:
                                messages.error(
                                    request,
                                    "You cannot hold more than 1000 shares of one company. Your current holding for "
                                    + company.name
                                    + ": "
                                    + str(userstockcount)
                                    + ".",
                                )
                            # Along with recording the transaction in the order book, we also need to indicate the order qty in the Investment Record table
                            # This was happening in pre_save_transaction_receiver, but stocks are getting added to escrow even if there is an error

                            # This is execute_trades part logic
                            transactions = Transaction.objects.all()
                            for transaction in transactions:
                                if transaction.mode.upper() == "SELL":
                                    _ = Sellstage.objects.create(
                                        order_id=transaction.id,
                                        user=transaction.user,
                                        company=transaction.company,
                                        num_stocks=transaction.num_stocks,
                                        orderprice=transaction.orderprice,
                                        status=transaction.status,
                                        sold=0,
                                    )
                                elif transaction.mode.upper() == "BUY":
                                    _ = Buystage.objects.create(
                                        order_id=transaction.id,
                                        user=transaction.user,
                                        company=transaction.company,
                                        num_stocks=transaction.num_stocks,
                                        orderprice=transaction.orderprice,
                                        status=transaction.status,
                                        bought=0,
                                    )
                                else:
                                    pass
                            buyorders = Buystage.objects.all()
                            sellorders = Sellstage.objects.all()
                            for buyorder in buyorders:
                                Transaction.objects.filter(
                                    id=buyorder.order_id
                                ).delete()
                            for sellorder in sellorders:
                                Transaction.objects.filter(
                                    id=sellorder.order_id
                                ).delete()

                            # #Debug code
                            # buyorders = Transaction.objects.all().filter(user=request.user, company=company)
                            # for buyorder in buyorders:
                            #     print('execute_trades called after buy order no.:' + str(buyorder.order_id))

                            # Calling execute_trades every time an order is placed
                            sql = "call execute_trades();"
                            conn = psycopg2.connect(
                                database=dbName,
                                user=dbUsername,
                                password=dbPassword,
                                host=dbHost,
                                port=dbPort,
                            )
                            cursor = conn.cursor()
                            cursor.execute(sql)
                            conn.commit()
                            cursor.close()
                            conn.close()

                            # Updating average buy price, total investment
                            moneyspent = 0.00
                            qty = 0
                            completedorders = CompletedOrders.objects.all().filter(
                                user=request.user, company=company, mode="BUY"
                            )
                            for order in completedorders:
                                moneyspent = Decimal(moneyspent) + (
                                    order.num_stocks * order.executionprice
                                )
                                qty = qty + order.num_stocks
                            if qty > 0:
                                obj, _ = InvestmentRecord.objects.get_or_create(
                                    user=request.user, company=company
                                )
                                obj.avgprice = round(
                                    round(moneyspent, 2) / round(qty, 2), 2
                                )
                                obj.save()
                                obj.investment = obj.avgprice * obj.stocks
                                obj.save()

                        else:
                            messages.error(
                                request,
                                "You do not have sufficient credits for this transaction.",
                            )
                    elif purchase_mode == "sell":
                        if quantity <= holding:
                            # Creating a sell transaction for the user
                            _ = Transaction.objects.create(
                                user=user,
                                company=company,
                                num_stocks=quantity,
                                orderprice=price,
                                mode=purchase_mode.upper()
                                # user_net_worth=InvestmentRecord.objects.calculate_net_worth(user)
                            )
                            print(
                                "User SELL order placed user="
                                + user.username
                                + " company="
                                + company.name
                                + " qty="
                                + str(quantity)
                            )

                            # Along with recording the transaction in the order book, we also need to indicate the order qty in the Investment Record table
                            # This was happening in pre_save_transaction_receiver, but stocks are getting added to escrow even if there is an error
                            obj, _ = InvestmentRecord.objects.get_or_create(
                                user=request.user, company=company
                            )
                            obj.sell_escrow = obj.sell_escrow + quantity
                            obj.stocks = obj.stocks - quantity
                            obj.save()
                            print("sell escrow = " + str(obj.sell_escrow))

                            messages.success(
                                request,
                                "SELL order placed for "
                                + str(quantity)
                                + " shares of "
                                + company.name
                                + " at "
                                + str(price),
                            )

                            buyorders = Buystage.objects.all().filter(company=company)

                            # if buyorders:
                            #     pass
                            # else:
                            # Creating an admin order to buy stocks whenever a sell order comes in
                            adminuser, _ = User.objects.get_or_create(
                                username="soc"
                            )  # username soc to buy all stocks
                            print("Admin username: " + adminuser.username)
                            _ = Transaction.objects.create(
                                user=adminuser,
                                company=company,
                                num_stocks=quantity,
                                orderprice=price,
                                mode="BUY",
                            )
                            obj, _ = InvestmentRecord.objects.get_or_create(
                                user=adminuser, company=company
                            )
                            obj.buy_escrow = obj.buy_escrow + quantity
                            obj.save()
                            print(
                                "Admin BUY order placed user="
                                + adminuser.username
                                + " company="
                                + company.name
                                + " qty="
                                + str(quantity)
                            )

                            # This is execute_trades part logic
                            transactions = Transaction.objects.all()
                            for transaction in transactions:
                                if transaction.mode.upper() == "SELL":
                                    _ = Sellstage.objects.create(
                                        order_id=transaction.id,
                                        user=transaction.user,
                                        company=transaction.company,
                                        num_stocks=transaction.num_stocks,
                                        orderprice=transaction.orderprice,
                                        status=transaction.status,
                                        sold=0,
                                    )
                                elif transaction.mode.upper() == "BUY":
                                    _ = Buystage.objects.create(
                                        order_id=transaction.id,
                                        user=transaction.user,
                                        company=transaction.company,
                                        num_stocks=transaction.num_stocks,
                                        orderprice=transaction.orderprice,
                                        status=transaction.status,
                                        bought=0,
                                    )
                                else:
                                    pass
                            buyorders = Buystage.objects.all()
                            sellorders = Sellstage.objects.all()
                            for buyorder in buyorders:
                                Transaction.objects.filter(
                                    id=buyorder.order_id
                                ).delete()
                            for sellorder in sellorders:
                                Transaction.objects.filter(
                                    id=sellorder.order_id
                                ).delete()

                            # Debug code
                            # sellorders = Transaction.objects.all().filter(user=request.user, company=company)
                            # for sellorder in sellorders:
                            #     print('execute_trades called after buy order no.:' + str(sellorder.order_id))

                            # Calling execute_trades every time an order is placed
                            sql = "call execute_trades();"
                            conn = psycopg2.connect(
                                database=dbName,
                                user=dbUsername,
                                password=dbPassword,
                                host=dbHost,
                                port=dbPort,
                            )
                            cursor = conn.cursor()
                            cursor.execute(sql)
                            conn.commit()
                            cursor.close()
                            conn.close()

                            obj, _ = InvestmentRecord.objects.get_or_create(
                                user=request.user, company=company
                            )
                            obj.investment = obj.avgprice * obj.stocks
                            obj.save()

                        else:
                            messages.error(
                                request,
                                "You do not have these many stocks to sell for "
                                + company.name
                                + ".",
                            )
                    else:
                        messages.error(request, "Please select a valid purchase mode.")
                elif mode == "schedule":
                    schedule_price = request.POST.get("price")
                    if purchase_mode == "buy":
                        _ = TransactionScheduler.objects.create(
                            user=user,
                            company=company,
                            num_stocks=quantity,
                            price=schedule_price,
                            mode=purchase_mode,
                        )
                        messages.success(request, "Request Submitted!")
                    elif purchase_mode == "sell":
                        _ = TransactionScheduler.objects.create(
                            user=user,
                            company=company,
                            num_stocks=quantity,
                            price=schedule_price,
                            mode=purchase_mode,
                        )
                        messages.success(request, "Request Submitted.")
                    else:
                        messages.error(request, "Please select a valid purchase mode.")
                else:
                    messages.error(request, "Please select a valid transaction mode.")
            else:
                messages.error(request, "Please enter a valid quantity.")
        else:
            msg = "The market is closed!"
            messages.info(request, msg)
        url = reverse("market:transaction", kwargs={"code": company.code})
        if request.is_ajax():
            return JsonResponse({"next_path": url})
        return HttpResponseRedirect(url)


# For Chart
class CompanyCMPChartData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None, *args, **kwargs):
        # Trying to introduce logic so that all price movements in the last 6 hours
        # If the player hasn't played a match in the last 6 hours, we give its last 15 price points
        today = datetime.combine(datetime.now().date(), datetime.min.time())
        matchduration = make_aware(today) - timedelta(hours=6)
        qs = CompanyCMPRecord.objects.filter(company__code=kwargs.get("code")).filter(
            timestamp__gte=matchduration
        )
        if qs.count() <= 1:
            qs = CompanyCMPRecord.objects.filter(company__code=kwargs.get("code"))
            qs = qs[:24]
        # if qs.count() > 30:
        #     qs = qs[:30]
        # if qs.count() > 15:
        #     qs = qs[:15]
        qs = reversed(qs)
        labels = []
        cmp_data = []
        for cmp_record in qs:
            labels.append(localtime(cmp_record.timestamp).strftime("%H:%M"))
            cmp_data.append(cmp_record.cmp)
        current_cmp = Company.objects.get(code=kwargs.get("code")).cmp
        # if cmp_data[-1] != current_cmp: # ??? I think this is checking if there is no movement in cmp
        #     labels.append(timezone.make_aware(datetime.now()).strftime('%H:%M'))
        #     cmp_data.append(current_cmp)

        data = {"labels": labels, "cmp_data": cmp_data}
        return Response(data)


class NewsView(LoginRequiredMixin, CountNewsMixin, View):
    template_name = "market/news.html"
    url = "news"

    def get(self, request, *args, **kwargs):
        UserNews.objects.get_by_user(request.user).update(read=True)
        queryset = News.objects.filter(is_active=True)
        return render(request, "market/news.html", {"object_list": queryset})


def executetrades(request):
    sql = "call execute_trades();"
    conn = psycopg2.connect(
        database=dbName, user=dbUsername, password=dbPassword, host=dbHost, port=dbPort
    )
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    print("Trades successfully executed.")
    message = "Trades successfully executed."
    # Test if you can get CMPs from 6 days ago and 7 days ago
    # print('Yahaan karenge debug')
    # ct = timezone.make_aware(datetime.now())
    # delta = ct - timedelta(days=7)
    # print(ct)
    # print(delta)

    # cmps = CompanyCMPRecord.objects.all().filter(company_id=234675).filter(updated__gte=delta)
    # for cmp in cmps:
    #     print(cmp.updated)
    #     print(cmp.cmp)

    # print(new)

    return redirect("/", {"executionsuccess": message})

    # Algo
    # Orders placed are collected in Transaction (new object created using Transaction.objects.create)
    # From Transaction table, orders are moved into buystage or sellstage based on mode and timestamp
    # All orders moved to buystage or sellstage are deleted from Transaction table
    # Buystage table is looped
    # For every buy order, the sellstage table is looped
    # If buyorder.company_id = sellorder.company_id: execution is possible
    # For buy order to be executed, user must have cash + escrow >= required investment for that order to complete
    # For every execution, the following steps need to be followed:
    # If buyorder.num_stocks < sellorder.num_stocks: buyorder will be completed, else if sellorder.num_stocks < buyorder.num_stocks, sellorder will be completed, else, both will be completed
    # Update sellorder entry in sellstage (num_stocks = num_stocks - qty, sold = sold + qty) (status = PART if partially completed)
    # Update buyorder entry in buystage (num_stocks = num_stocks - qty, bought = sold + qty) (status = PART if partially completed)
    # Subtract qty from InvestmentRecord.sell_escrow for sellorder
    # Subtract qty from InvestmentRecord.buy_escrow and add qty to IR.stocks for buyorder
    # Subtract credits from buyer
    # Subtract from escrow, if it spills over, subtract the spillover from user.cash
    # Add credits to seller
    # Add to user.cash
    # buyorder and sellorder are added to CompletedOrders with order details and status as PART or COMPLETED
    # If user does not have enough credits, order is moved to CancelledOrders with reason 'Insufficient credits'
    # That order is deleted from buystage
    # buyorder.user_id's escrow for that order is released
    # After every execution, delete all orders from buystage and sellstage that have num_stocks = 0 (which means they are completed)


def innings_change(request):
    form = ScoreCardForm(request.POST or None)
    match, _ = CurrentMatch.objects.get_or_create()
    first = match.batting_team
    if first == match.home_team:
        match.batting_team = match.away_team
    else:
        match.batting_team = match.home_team
    match.save()
    inningschangesuccess = "Innings changed successfully."
    # , 'batsman': batsman, 'nonstriker': nonstriker, 'bowler':bowler, 'submitbutton':submitbutton}
    return redirect("/", {"inningschangesuccess": inningschangesuccess})


"""def dashboard(request):
    form = ScoreCardForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        submitbutton = "Submit"
        form = ScoreCardForm(request.POST or None)
        batsman = ''
        bowler = ''
        nonstriker = ''
        if form.is_valid():
            batsman = form.cleaned_data.get("batsman")
            bowler = form.cleaned_data.get("bowler")
            nonstriker = form.cleaned_data.get("nonstriker")
            print('Batsman is ' + batsman)
            print('Bowler is ' + bowler)
            print('Non-striker is ' + nonstriker)
        context = {'form': form, 'batsman': batsman, 'nonstriker': nonstriker, 'bowler':bowler, 'submitbutton':submitbutton}
        return render(request, 'market/trial.html', context)
    else:
        context = {'form':form}
        return render(request, 'market/dashboard.html')"""


class MatchCreationView(LoginRequiredMixin, CountNewsMixin, View):
    template_name = "market/match_details.html"
    url = "match"

    def get(self, request, *args, **kwargs):
        form = MatchCreationForm(request.POST or None, request.FILES or None)
        # UserNews.objects.get_by_user(request.user).update(read=True)
        # queryset = News.objects.filter(is_active=True)
        context = {"form": form}
        return render(request, "market/match_details.html", context)

    def post(self, request, *args, **kwargs):
        # This code will run whenever the submit button is pressed on the Match Creation form.
        # Before displaying the score card dashboard, we need to create 22 entries in the 'Match' table with the players that have been selected in the Match form.
        # submitbutton = request.POST.get("submit")

        form = MatchCreationForm(request.POST or None)

        # form = ScoreCardForm(request.POST or None)

        # if form.is_valid():
        #     batsman = form.cleaned_data.get("batsman")
        #     bowler = form.cleaned_data.get("bowler")
        #     nonstriker = form.cleaned_data.get("nonstriker")
        #     runs_batsman = form.cleaned_data.get("runs_batsman")
        #     print(batsman)
        #     print(bowler)
        #     print(nonstriker)
        #     print(runs_batsman)

        match_id = 0
        home_team = ""
        away_team = ""
        home_team_players = []
        away_team_players = []

        # form = ScoreCardForm(None) # We need a blank form to start
        if form.is_valid():
            match_id = form.cleaned_data.get("match_id")
            home_team = form.cleaned_data.get("home_team")
            away_team = form.cleaned_data.get("away_team")
            home_team_players = form.cleaned_data.get(
                "home_team_players"
            )  # This would be a list of player ids
            away_team_players = form.cleaned_data.get(
                "away_team_players"
            )  # This would be a list of player ids
            batting_team = form.cleaned_data.get("batting_team")
            print(match_id)
            print(home_team)
            print(away_team)
            print(home_team_players)
            print(away_team_players)
            print(batting_team)
            # Data has been collected in variables, now pushing them into the db
            conn = psycopg2.connect(
                database=dbName,
                user=dbUsername,
                password=dbPassword,
                host=dbHost,
                port=dbPort,
            )
            cursor = conn.cursor()
            # sql = "delete from market_currentmatch where match_id <> " + str(match_id) + ";"
            sql = "delete from market_currentmatch;"
            cursor.execute(sql)
            # You could do CurrentMatch.objects.delete()
            sql = (
                "insert into market_currentmatch (match_id, home_team, away_team, batting_team) values ("
                + str(match_id)
                + ", '"
                + home_team
                + "', '"
                + away_team
                + "', '"
                + batting_team
                + "');"
            )
            cursor.execute(sql)
            sql = "call update_valuations_all();"
            cursor.execute(sql)
            # You could do CurrentMatch.objects.create(match_id=match_id, home_team=home_team, away_team=away_team, batting_team=batting_team)

            _ = UpcomingMatches.objects.filter(match_id=match_id).delete()

            for home_team_player in home_team_players:
                player = PlayerStats.objects.all().filter(id=int(home_team_player))
                for p in player:
                    print("Player id: " + str(p.id))
                    print("Player name: " + p.name)
                    print("Player team: " + p.ipl_team)
                sql = (
                    "insert into market_match (runs, balls_faced, fours, sixes, catches, stumpings, runouts, dismissed, balls_bowled, runs_conceded, wickets, match_id, player_id, name, team, updated) values (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,"
                    + str(match_id)
                    + ", '"
                    + str(p.id)
                    + "', '"
                    + p.name
                    + "', '"
                    + p.ipl_team
                    + "', current_timestamp);"
                )
                cursor.execute(sql)
                # _ = AllMatches.objects.create(match_id=match_id, player_id=p.id, name=p.name, team=p.ipl_team)

            for away_team_player in away_team_players:
                player = PlayerStats.objects.all().filter(id=int(away_team_player))
                for p in player:
                    print("Player id: " + str(p.id))
                    print("Player name: " + p.name)
                    print("Player team: " + p.ipl_team)
                sql = (
                    "insert into market_match (runs, balls_faced, fours, sixes, catches, stumpings, runouts, dismissed, balls_bowled, runs_conceded, wickets, match_id, player_id, name, team, updated) values (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,"
                    + str(match_id)
                    + ", '"
                    + str(p.id)
                    + "', '"
                    + p.name
                    + "', '"
                    + p.ipl_team
                    + "', current_timestamp);"
                )
                cursor.execute(sql)
                # _ = AllMatches.objects.create(match_id=match_id, player_id=p.id, name=p.name, team=p.ipl_team)

            ct = timezone.make_aware(datetime.now())
            matches = Match.objects.all()
            for match in matches:
                delta = ct - match.updated
                if delta > timedelta(days=7):
                    # Updating player stat entry for outgoing match performance
                    stat, _ = PlayerStats.objects.get_or_create(id=match.player_id)
                    stat.matches += 1
                    stat.runs += match.runs
                    stat.balls_faced += match.balls_faced
                    stat.fours += match.fours
                    stat.sixes += match.sixes
                    stat.catches += match.catches
                    stat.stumpings += match.stumpings
                    stat.balls_bowled += match.balls_bowled
                    stat.runs_conceded += match.runs_conceded
                    stat.wickets += match.wickets
                    if match.balls_faced > 0:
                        stat.batting_innings += 1
                        if match.dismissed == 0:
                            stat.notouts += 1
                    if match.balls_bowled > 0:
                        stat.bowling_innings += 1
                    if match.runs >= 100:
                        stat.hundreds += 1
                    elif match.runs < 100 and match.runs >= 50:
                        stat.fifties += 1
                    # Use substring features to compare if highest score and bbi have been broken
                    if stat.highest[-1] != "*":
                        high = int(stat.highest)
                    else:
                        high = int(stat.highest[:-1])
                    if match.runs > high and match.dismissed == 1:
                        stat.highest = str(match.runs)
                    elif match.runs >= int(high) and match.dismissed == 0:
                        stat.highest = str(match.runs) + "*"

                    if stat.bbi != "0":
                        if int(stat.bbi[0]) < match.wickets:
                            stat.bbi = (
                                str(match.wickets) + "/" + str(match.runs_conceded)
                            )
                        elif int(stat.bbi[0]) == match.wickets:
                            if int(stat.bbi[2:]) > match.runs_conceded:
                                stat.bbi = (
                                    str(match.wickets) + "/" + str(match.runs_conceded)
                                )
                    stat.save()

                    if stat.runs > 0:
                        if (stat.batting_innings - stat.notouts) > 0:
                            battingavg = round(
                                stat.runs / (stat.batting_innings - stat.notouts), 2
                            )
                            stat.batting_average = battingavg
                        battingsr = round((stat.runs / stat.balls_faced) * 100.00, 2)
                        stat.batting_sr = battingsr
                    if stat.balls_bowled > 0:
                        rpo = round((stat.runs_conceded / stat.balls_bowled) * 6.00, 2)
                        stat.economy = rpo
                        if stat.wickets > 0:
                            bowlingavg = round((stat.runs_conceded / stat.wickets), 2)
                            stat.bowling_average = bowlingavg
                            bowlingsr = round(stat.balls_bowled / stat.wickets, 2)
                            stat.bowling_sr = bowlingsr

                    stat.bbm = stat.bbi

                    stat.save()

                    _ = AllMatches.objects.create(
                        match_id=match.match_id,
                        name=match.name,
                        team=match.team,
                        runs=match.runs,
                        balls_faced=match.balls_faced,
                        fours=match.fours,
                        sixes=match.sixes,
                        catches=match.catches,
                        stumpings=match.stumpings,
                        runouts=match.runouts,
                        balls_bowled=match.balls_bowled,
                        runs_conceded=match.runs_conceded,
                        wickets=match.wickets,
                        dismissed=match.dismissed,
                        updated=match.updated,
                        player=match.player,
                    )
                    match.delete()
            sql = "call calculate_valuations();"
            cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()

            # obj, _ = Match.objects.get_or_create(id=146)
            # print('Player: '+obj.name)
            # print('Match ID: '+str(obj.match_id))
            # print('Timestamp: '+str(obj.updated))
            # ct = timezone.make_aware(datetime.now())
            # delta = ct-obj.updated
            # if delta > timedelta(days=6):
            #     print('Delta:')
            #     print(delta)
            # new = obj.updated + timedelta(days=2)

            # This has to be done for all outgoing matches
            # outgoingmatches = Match.objects.filter() [Add a filter so that only outgoing matches are collected in this]
            # [Add data from all these matches to playerstats (Update every player's entry)]
            # Add outgoing match data into AllMatches
            # for outgoingmatch in outgoingmatches:
            #     _ = AllMatches.objects.create(
            #         match_id = match.match_id,
            #         name = match.name,
            #         team = match.team,
            #         runs = match.runs,
            #         balls_faced = match.balls_faced,
            #         fours = match.fours,
            #         sixes = match.sixes,
            #         catches = match.catches,
            #         stumpings = match.stumpings,
            #         runouts = match.runouts,
            #         balls_bowled = match.balls_bowled,
            #         runs_conceded = match.runs_conceded,
            #         wickets = match.wickets,
            #         dismissed = match.dismissed,
            #         updated = match.updated,
            #         player = match.player
            #     )
            # Match.objects.filter(where id in outgoingmatches).delete()
            # Edit calculate_valuations to 'update' system_valuation for all players in PlayerValuations instead of inserting.

            # return redirect('/match/dashboard/?match_id=' + match_id +'&home_team=' + home_team + '&away_team=' + away_team)
        context = {
            "form": form,
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
        }
        return render(request, "market/match_details.html", context)


def match_create_view(request):
    pass
    # form = MatchCreationForm()
    # if request.method == 'POST':
    #     form = MatchCreationForm(request.POST)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('match_add')
    # return render(request, 'market/match_details.html', {'form': form})


def match_update_view(request, pk):
    pass
    # match = get_object_or_404(Match, pk=pk)
    # form = MatchCreationForm(instance=match)
    # if request.method == 'POST':
    #     form = MatchCreationForm(request.POST, instance=match)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('match_change', pk=pk)
    # return render(request, 'market/match_details.html', {'form': form})


# AJAX
def load_players(request):
    home_team = request.GET.get("home_team")
    away_team = request.GET.get("away_team")
    home_team_players = PlayerStats.objects.filter(ipl_team=home_team).all()
    away_team_players = PlayerStats.objects.filter(ipl_team=away_team).all()
    return render(
        request,
        "market/player_check_list_options.html",
        {
            "home_team_players": home_team_players,
            "away_team_players": away_team_players,
        },
    )
    # return JsonResponse(list(cities.values('id', 'name')), safe=False)


def load_order_details(request):
    num_stocks = request.GET.get("")


class AllPlayersView(LoginRequiredMixin, CountNewsMixin, ListView):
    template_name = "market/all_players.html"
    url = "allplayers"
    queryset = PlayerValuations.objects.all().order_by("-current_form")

    def get_context_data(self, *args, **kwargs):
        context = super(AllPlayersView, self).get_context_data(*args, **kwargs)
        context.update({"companies": Company.objects.all()})

        return context


class UpcomingMatchPlayersView(LoginRequiredMixin, CountNewsMixin, ListView):
    template_name = "market/upcoming_match_players.html"
    url = "upcomingmatchplayers"
    queryset = PlayerValuations.objects.all().order_by("-current_form")

    def get_context_data(self, *args, **kwargs):
        context = super(UpcomingMatchPlayersView, self).get_context_data(
            *args, **kwargs
        )
        hometeam = ""
        awayteam = ""
        upcomingmatches = UpcomingMatches.objects.all()
        if upcomingmatches.count() == 1:
            for m in upcomingmatches:
                hometeam = m.home_team
                awayteam = m.away_team
            context["m1homename"] = hometeam
            context["m1awayname"] = awayteam
            context["match1home"] = PlayerValuations.objects.filter(
                team__icontains=hometeam
            ).filter(company__cmp__gt=0)
            context["match1away"] = PlayerValuations.objects.filter(
                team__icontains=awayteam
            ).filter(company__cmp__gt=0)
        elif upcomingmatches.count() == 2:
            hometeams = []
            awayteams = []
            for m in upcomingmatches:
                hometeams.append(m.home_team)
                awayteams.append(m.away_team)
            context["m1homename"] = hometeams[0]
            context["m1awayname"] = awayteams[0]
            context["match1home"] = PlayerValuations.objects.filter(
                team__icontains=hometeams[0]
            ).filter(company__cmp__gt=0)
            context["match1away"] = PlayerValuations.objects.filter(
                team__icontains=awayteams[0]
            ).filter(company__cmp__gt=0)
            context["m2homename"] = hometeams[1]
            context["m2awayname"] = awayteams[1]
            context["match2home"] = PlayerValuations.objects.filter(
                team__icontains=hometeams[1]
            ).filter(company__cmp__gt=0)
            context["match2away"] = PlayerValuations.objects.filter(
                team__icontains=awayteams[1]
            ).filter(company__cmp__gt=0)
        match, _ = CurrentMatch.objects.get_or_create()
        context["company_list"] = PlayerValuations.objects.filter(
            Q(team__icontains=match.home_team) | Q(team__icontains=match.away_team)
        )
        context["purchase_modes"] = ["buy", "sell"]
        return context

    # def post(self, request, *args, **kwargs):
    #     pass
    # This method will enable us to transact stocks from the list of players


# CODE TO BE RUN FOR POPULATING BALL BY BALL SCORE DATA - START
# Making a list of all matches available in the ballbyball table


# CODE TO BE RUN FOR POPULATING BALL BY BALL SCORE DATA - END


class DashboardView(LoginRequiredMixin, CountNewsMixin, View):
    template_name = "market/dashboard.html"
    url = "dashboard"

    def get(self, request, *args, **kwargs):
        match, _ = CurrentMatch.objects.get_or_create()
        match_id = match.match_id
        home_team = match.home_team
        away_team = match.away_team
        batting_team = match.batting_team
        form = ScoreCardForm(request.POST or None, request.FILES or None)
        context = {
            "form": form,
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
        }
        return render(request, "market/dashboard.html", context)

    def post(self, request, *args, **kwargs):
        match, _ = CurrentMatch.objects.get_or_create()
        match_id = match.match_id
        home_team = match.home_team
        away_team = match.away_team
        # batting_team = match.batting_team

        form = ScoreCardForm(request.POST)
        batsman = 0
        bowler = 0
        runs_batsman = 0
        runs_extra = 0
        extra_type = 0
        dismissal_type = 0
        dismissed_batsman = 0
        fielder = 0
        if form.is_valid():
            batsman = form.cleaned_data.get("batsman")
            bowler = form.cleaned_data.get("bowler")
            # nonstriker = form.cleaned_data.get("nonstriker")
            runs_batsman = form.cleaned_data.get("runs_batsman")
            runs_extra = form.cleaned_data.get("runs_extra")
            extra_type = form.cleaned_data.get("extra_type")
            dismissal_type = form.cleaned_data.get("dismissal_type")
            dismissed_batsman = form.cleaned_data.get("dismissed_batsman")
            fielder = form.cleaned_data.get("fielder")
            # ts = time.time()
            # timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            batsmanco, _ = Company.objects.get_or_create(id=batsman)
            bowlerco, _ = Company.objects.get_or_create(id=bowler)

            batsman, _ = Match.objects.get_or_create(
                player_id=batsman, match_id=match_id
            )
            # nonstriker, _ = Match.objects.get_or_create(player_id=nonstriker,match_id=match_id)
            bowler, _ = Match.objects.get_or_create(player_id=bowler, match_id=match_id)
            fielder, _ = Match.objects.get_or_create(
                player_id=fielder, match_id=match_id
            )
            dismissed_batsman, _ = Match.objects.get_or_create(
                player_id=dismissed_batsman, match_id=match_id
            )

            # Runs can get added to PlayerStats as is, the currentform multiplier needs to take into consideration what how good a bowler they came against
            # How about this -> runs * bowlercmp/batsmancmp * 10
            # Similarly for wickets -> wicket * batsmancmp/bowlercmp * 1500

            # For this to happen, Currentform will can not be recalculated from scratch every time, it needs to be incremented from its previous value at every ball (We have cfcmp)
            # But how to maintain a 7-day compartment for cfcmp in this case?
            # We have CompanyCMPRecord for all price movements. Present CMP,
            # (CMP at T-6 days)-(CMP at T-7 days) = jump/fall in price for the outgoing timespan
            # Using the new update_valuations, we get by how much the price is going to jump/fall for the incoming timespan (ball)
            # Data from Match table can be used to update PlayerStats, but update_valuations needs to take a different route

            # Solution - added a column called cmpchange to CompanyCMPRecord which will give us the cmp change at every ball.  This can be populated separately as well by taking differences between succesive CMP records, but this is more convenient

            batcontextcmp = Decimal(0.00)
            ballcontextcmp = Decimal(0.00)
            fieldcontextcmp = Decimal(0.00)
            dismissedcontextcmp = Decimal(0.00)

            batmultiplier = Decimal(bowlerco.cmp / batsmanco.cmp)
            ballmultiplier = Decimal(batsmanco.cmp / bowlerco.cmp)

            batsman.runs = batsman.runs + int(runs_batsman)
            batcontextcmp = batcontextcmp + (
                Decimal(runs_batsman) * batmultiplier * Decimal(2.00)
            )

            bowler.runs_conceded = bowler.runs_conceded + int(runs_batsman)
            if int(runs_batsman) == 4:
                batsman.fours = batsman.fours + 1
                batcontextcmp = batcontextcmp + (batmultiplier * Decimal(5.00))
            elif int(runs_batsman) == 6:
                batsman.sixes = batsman.sixes + 1
                batcontextcmp = batcontextcmp + (batmultiplier * Decimal(15.00))

            if int(runs_extra) == 0:
                bowler.balls_bowled = bowler.balls_bowled + 1
                batsman.balls_faced = batsman.balls_faced + 1
            else:
                if int(extra_type) == 1 or int(extra_type) == 2:
                    bowler.runs_conceded = bowler.runs_conceded + int(runs_extra)
                elif int(extra_type) == 3 or int(extra_type) == 4:
                    bowler.balls_bowled = bowler.balls_bowled + 1

            if int(dismissal_type) == 1:
                dismissed_batsman.dismissed = 1
                fielder.catches += 1
                bowler.wickets += 1

            elif int(dismissal_type) == 2 or int(dismissal_type) == 3:
                dismissed_batsman.dismissed = 1
                bowler.wickets += 1

            elif int(dismissal_type) == 4:
                dismissed_batsman.dismissed = 1
                # fielder.runouts = fielder.runouts + 1

            elif int(dismissal_type) == 5:
                dismissed_batsman.dismissed = 1
                fielder.stumpings += 1
                bowler.wickets += 1

            batsman.save()
            bowler.save()
            # nonstriker.save()
            fielder.save()
            dismissed_batsman.save()

            # SQL code to be pasted here - pasted in scratchpad.sql in C:\Users\Pranay Karwa\Projects\WallStreet-master

            conn = psycopg2.connect(
                database=dbName,
                user=dbUsername,
                password=dbPassword,
                host=dbHost,
                port=dbPort,
            )
            cursor = conn.cursor()
            sql = "call update_valuations_new(" + str(batsman.player_id) + ");"
            cursor.execute(sql)
            # sql = 'call update_valuations(' + str(nonstriker.player_id) + ');' # No need to call for nonstriker. If he is runout, it'll be taken care of with dismissed_batsman
            # cursor.execute(sql)
            sql = "call update_valuations_new(" + str(bowler.player_id) + ");"
            cursor.execute(sql)
            sql = "call update_valuations_new(" + str(fielder.player_id) + ");"
            cursor.execute(sql)
            if dismissed_batsman.player_id != batsman.player_id:
                sql = (
                    "call update_valuations_new("
                    + str(dismissed_batsman.player_id)
                    + ");"
                )
                cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()

        context = {
            "form": form,
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
        }
        # , 'batsman': batsman, 'nonstriker': nonstriker, 'bowler':bowler, 'submitbutton':submitbutton}
        return render(request, "market/dashboard.html", context)


# Open a connection pool and keep them open.  Whenever the db needs to be hit, you fetch a connection, do whatever you need to, and put it back in the pool.


def search(request):
    query = ""

    query = request.GET["query"].strip()
    allCompanies = Company.objects.all().filter(name__icontains=query)
    context = {
        "allCompanies": allCompanies,
        "query": query,
    }
    return render(request, "market/search.html", context)


class TradingDashboard(LoginRequiredMixin, TemplateView):
    template_name = "market/trading_dashboard.html"

    def get(self, request, *args, **kwargs):
        stockchart_form = StockSearchForm()
        all_orders = Order.objects.filter(user=self.request.user).order_by("-id")
        completed_orders = all_orders.filter(status="Completed")
        companies_bought = completed_orders.values_list("company__code", flat=True)
        positions = []
        for company in companies_bought:
            company_obj = Company.objects.get(code=company)
            net_qty = (
                completed_orders.filter(company__code=company).aggregate(
                    Sum("num_stocks")
                )["num_stocks__sum"]
                or 0
            )
            avg_price = (
                completed_orders.filter(company__code=company).aggregate(
                    Avg("execution_price")
                )["execution_price__avg"]
                or 0
            )
            avg_price = round(avg_price, 2)
            current_mkt_price = company_obj.cmp or 0
            pnl = round(net_qty * (current_mkt_price - avg_price), 2)

            positions.append(
                {
                    "company_name": company,
                    "net_qty": net_qty,
                    "avg_price": avg_price,
                    "cmp": current_mkt_price,
                    "pnl": pnl,
                }
            )

        return self.render_to_response(
            {
                "companies": Company.objects.all(),
                "stockchart_form": stockchart_form,
                "orders": all_orders,
                "positions": positions,
                "holdings": InvestmentRecord.objects.filter(user=self.request.user),
                "watchlists": list(
                    Watch.objects.filter(user=self.request.user).values(
                        "watch_name", "id"
                    )
                ),
            }
        )


class OrderBookView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response({"orders": Order.objects.all()})


class WatchList(APIView):
    def get(self, request, pk):
        watch = get_object_or_404(Watch, pk=pk)
        stocks = list(watch.stocks.all().values("id", "name", "code", "cmp"))
        return Response({"stocks": stocks})

    def post(self, request):
        request.data._mutable = True
        request.data["user"] = request.user
        request.data._mutable = False
        serializer = WatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyCMPRecordView(APIView):
    authentication_classes = []
    permission_classes = []
    event_batch = 20

    def get(self, request, company_id, chart_type, format=None, *args, **kwargs):
        company = get_object_or_404(Company, pk=company_id)
        cmp_records = CompanyCMPRecord.objects.filter(company_id=company_id)
        candlestick = chart_type == "candlestick"
        data = []
        line = chart_type == "line"
        cmp_records = cmp_records.order_by("timestamp")
        if candlestick and cmp_records:
            paginator = Paginator(cmp_records, self.event_batch)
            for page_no in paginator.page_range:
                current_page = paginator.get_page(page_no)
                current_qs = list(current_page.object_list)
                open_price = current_qs[-1].cmp
                close_price = current_qs[0].cmp
                index_high_price, high_price = max(
                    enumerate([c.cmp for c in current_qs]), key=operator.itemgetter(1)
                )
                index_low_price, low_price = min(
                    enumerate([c.cmp for c in current_qs]), key=operator.itemgetter(1)
                )
                timestamp = current_qs[-1].timestamp.timestamp()
                data.append(
                    {
                        "time": timestamp,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "company_name": f"{company.name}-{company.code}",
                    }
                )
        elif line:
            for each_cmp in cmp_records:
                data.append(
                    {"time": each_cmp.timestamp.timestamp(), "value": each_cmp.cmp}
                )
        return Response(data)


class OrderCreationView(FormView):
    form_class = OrderCreationForm
    template_name = "market/order_book_modal.html"

    def get_company(self, company_id):
        company = get_object_or_404(Company, pk=company_id)
        latest_cmp = CompanyCMPRecord.objects.filter(company=company).latest("id").cmp
        company.cmp = latest_cmp
        company.save(update_fields=["cmp"])
        return company

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        company_id = request.GET.get("company_id")
        quantity = request.GET.get("quantity", "")
        execution_price = request.GET.get("execution_price", "")
        total_amount = None
        if quantity and execution_price:
            total_amount = round(float(quantity) * float(execution_price), 2)
        company = self.get_company(company_id)
        context = self.get_context_data(form=form)
        context.update(
            {
                "company": company,
                "company_id": company.id,
                "player_name": company.name,
                "player_code": company.code,
                "player_cmp": company.cmp,
                "quantity": quantity,
                "execution_price": execution_price,
                "total_amount": total_amount,
            }
        )
        return self.render_to_response(context=context)

    @staticmethod
    def _get_message(order):
        message = f"Your order {order.order_id} has been placed!<br/>"
        message += f"&nbsp;Details<br/>"
        message += f"&nbsp;{order.company.name}({order.company.code})<br/>"
        message += f"&nbsp;Price: {order.execution_price}<br/>"
        message += f"&nbsp;Quantity: {order.num_stocks}<br/>"
        message += f"&nbsp;Total amount: {order.num_stocks * order.execution_price} INR"
        return message

    def post(self, request, *args, **kwargs):
        company_id = request.POST.get("company_id")
        company = self.get_company(company_id)
        form = self.get_form()
        if form.is_valid():
            order = form.save(commit=False)
            order.company = company
            order.user = self.request.user
            order.save()
            message = self._get_message(order)
            message_api.success(request, mark_safe(message))
        else:
            message_api.error(request, " Failed to create order")
        return HttpResponseRedirect("")


class PlayerDetails(TemplateView):
    template_name = "market/player_details.html"

    def get(self, request, player_id, *args, **kwargs):
        company = get_object_or_404(Company, pk=player_id)
        try:
            latest_cmp = (
                CompanyCMPRecord.objects.filter(company=company).latest("id").cmp
            )
        except CompanyCMPRecord.DoesNotExist:
            latest_cmp = None
        return self.render_to_response({"player": company, "latest_cmp": latest_cmp,})


class SearchNavBarView(FormView):
    form_class = SearchNavBarForm
    template_name = "base/navbar.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get(self, request, *args, **kwargs):
        searchbarform = self.get_form()
        context = self.get_context_data(form=form)
        context.update(
            {"searchbarform": searchbarform,}
        )
        return self.render_to_response(context=context)


class GetCompanies(APIView):
    def get(self, request):
        data = {
            "companies": list(
                Company.objects.filter().values("name", "code", "cmp", "id")
            )
        }
        return Response(data)


class TransactShares(APIView):
    def post(self, request):
        parameters = request.POST
        transaction_form = TransactStockForm(parameters)
        company_id = parameters.get("company_id")
        company = get_object_or_404(Company, pk=company_id)
        txn_data = {
            "orderprice": parameters.get("cmp"),
            "mode": parameters.get("order_mode"),
            "user": request.user,
            "company": company,
            "num_stocks": parameters.get("quantity"),
        }
        transaction_form = TransactStockForm(txn_data)
        if transaction_form.is_valid():
            Transaction.objects.create(**txn_data)
            if txn_data["mode"] == "buy":
                message_api.success(request, mark_safe("Shares bought successfully!"))
            else:
                message_api.success(request, mark_safe("Shares sold successfully!"))
            return Response({"txn_status": "Shares executed successfully!"})
        else:
            message_api.error(request, mark_safe(transaction_form.errors["__all__"]))
            return Response({"error_msg": transaction_form.errors["__all__"]})
