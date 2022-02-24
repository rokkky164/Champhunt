import random
import json

from decimal import Decimal

from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from django.urls import reverse
from django.utils.functional import cached_property

from accounts.models import User
import channels.layers
from django.dispatch import receiver
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync


home_team = ""
away_team = ""

TRANSACTION_MODES = (("buy", "BUY"), ("sell", "SELL"))

CAP_TYPES = (
    ("small", "Small Cap"),
    ("mid", "Mid Cap"),
    ("large", "Large Cap"),
)

EXTRA_TYPES = ((0, "none"), (1, "wides"), (2, "no-ball"), (3, "byes"), (4, "legbyes"))

DISMISSAL_TYPES = (
    (0, "none"),
    (1, "caught"),
    (2, "bowled"),
    (3, "lbw"),
    (4, "runout"),
    (5, "stumped"),
    (6, "retired-hurt"),
)

INDUSTRY_CHOICES = (
    ("Batsman", "Batsman"),
    ("Bowler", "Bowler"),
    ("Batting Allrounder", "Batting Allrounder"),
    ("Bowling Allrounder", "Bowling Allrounder"),
)

CMP_CHANGE_REASONS = (
    ("0 run scored", "0 run scored"),
    ("1 run scored", "1 run scored"),
    ("2 runs scored", "2 runs scored"),
    ("3 runs scored", "3 runs scored"),
    ("4 runs scored", "4 runs scored"),
    ("5 runs scored", "5 runs scored"),
    ("6 runs scored", "6 runs scored"),
    ("No ball bowled", "No ball bowled"),
    ("Wide ball bowled", "Wide ball bowled"),
    ("Bye run scored", "Bye run scored"),
    ("Clean Bowled", "Clean Bowled"),
    ("Hit Wicket", "Hit Wicket"),
    ("Run out", "Run out"),
)

ORDER_STATUS = (
    ("Placed", "Placed"),
    ("Pending", "Pending"),
    ("Order Matched", "Order Mathced"),
    ("Cancelled", "Cancelled"),
    ("Failed", "Failed"),
    ("Completed", "Completed"),
)

FORMAT_CHOICES = (
    ("T20", "T20"),
    ("T20I", "T20I"),
    ("ODI", "ODI"),
    ("Test", "Test"),
)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


class Company(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50, unique=True)
    quantity = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    cmp = models.DecimalField(
        max_digits=20, decimal_places=2, default=0.00
    )  # Why does this appear in blue? > its a python keyword
    cfcmp = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cap_type = models.CharField(max_length=20, choices=CAP_TYPES, blank=True, null=True)
    stocks_bought = models.IntegerField(default=0)
    industry = models.CharField(
        max_length=120, choices=INDUSTRY_CHOICES, blank=True, null=True
    )
    first_loading_time = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["cap_type", "code"]

    def __str__(self):
        return self.name

    @cached_property
    def get_cap(self):
        cap_type = self.cap_type
        if cap_type == "small":
            return "Small Cap"
        elif cap_type == "mid":
            return "Mid Cap"
        return "Large Cap"

    def get_absolute_url(self):
        return reverse("market:transaction", kwargs={"code": self.code})


# def post_save_company_receiver(
#     sender, instance, created, *args, **kwargs
# ):  # I suspect this is the function creating the Investment Record object upon page visiting.
#     if created:
#         # Create Investment Records of the company with each existing user
#         user_qs = User.objects.all()
#         for user in user_qs:
#             obj, create = InvestmentRecord.objects.get_or_create(
#                 user=user, company=instance
#             )

#         # Create CMP Record of the company
#         CompanyCMPRecord.objects.create(company=instance, cmp=instance.cmp)


# post_save.connect(post_save_company_receiver, sender=Company)


class CompanyValuations(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50, unique=True)
    mkt_qty = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    # market cap should be calculated, not stored. Consider removing this field. - Pranay
    cap = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    cmp = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cap_type = models.CharField(max_length=20, choices=CAP_TYPES, blank=True, null=True)
    stocks_bought = models.IntegerField(default=0)
    current_form = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    team = models.CharField(max_length=50, default="NA")


class CompanyCMPRecord(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    cmp = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    timestamp = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)  # This field is redundant.
    cmpchange = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    contextcmp = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    event = models.CharField(
        max_length=200, choices=CMP_CHANGE_REASONS, blank=True, null=True
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return self.company.code


@receiver(post_save, sender=CompanyCMPRecord)
def cmp_record_observer(sender, instance, created, **kwargs):
    if created:
        company = instance.company
        company.cmp = instance.cmp
        company.save()
        layer = channels.layers.get_channel_layer()
        async_to_sync(layer.group_send)(
            "cmp_data",
            {
                "type": "get.cmp",
                "data": json.dumps(
                    {
                        "company_id": instance.company.id,
                        "cmp": instance.cmp,
                        "id": instance.id,
                        "timestamp": instance.timestamp.timestamp(),
                    },
                    cls=DecimalEncoder,
                ),
            },
        )


class TransactionQueryset(models.query.QuerySet):
    def get_by_user(self, user):
        return self.filter(user=user)

    def get_by_company(self, company):
        return self.filter(company=company)

    def get_by_user_and_company(self, user, company):
        return self.filter(user=user, company=company)


class TransactionManager(models.Manager):
    def get_queryset(self):
        return TransactionQueryset(self.model, using=self._db)

    def get_by_user(self, user):
        return self.get_queryset().get_by_user(user=user)

    def get_by_company(self, company):
        return self.get_queryset().get_by_company(company=company)

    def get_by_user_and_company(self, user, company):
        return self.get_queryset().get_by_user_and_company(user=user, company=company)


class AbstractTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    num_stocks = models.IntegerField(default=0)
    first_loading_time = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default="OPEN")
    objects = TransactionManager()

    class Meta:
        abstract = True


# We can collect all orders here and segregate them into buystage and sellstage from here
# To make this table as light as possible, we need to get rid of unwanted fields
# Price and user net worth can be get rid of, we'll calculate those in the stored proc
# Introducing status field here for order status
class Transaction(AbstractTransaction):
    orderprice = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    mode = models.CharField(max_length=10, choices=TRANSACTION_MODES)

    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user} - {company}".format(
            user=self.user.username, company=self.company.name
        )


class Buybook(AbstractTransaction):
    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user} - {company}".format(
            user=self.user.username, company=self.company.name
        )


class Sellbook(AbstractTransaction):
    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user} - {company}".format(
            user=self.user.username, company=self.company.name
        )


# Staging table for buy orders
class Buystage(AbstractTransaction):
    order_id = models.IntegerField(default=0)
    bought = models.IntegerField(default=0)
    orderprice = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user} - {company}".format(
            user=self.user.username, company=self.company.name
        )


# Staging table for sell orders
class Sellstage(AbstractTransaction):
    order_id = models.IntegerField(default=0)
    sold = models.IntegerField(default=0)
    orderprice = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user} - {company}".format(
            user=self.user.username, company=self.company.name
        )


def get_order_id():
    return "".join(random.choices("NOPQRSTUVWXYZ1234567890", k=10))


class AbstractOrder(models.Model):
    order_id = models.CharField(default=get_order_id, max_length=10)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    num_stocks = models.IntegerField(default=0)
    mode = models.CharField(max_length=10, default="NA")
    orderprice = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    first_loading_time = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS, default=ORDER_STATUS[0][0]
    )

    objects = TransactionManager()

    class Meta:
        abstract = True


class Order(AbstractOrder):
    reason = models.CharField(max_length=50, default="", blank=True)
    execution_price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    brokerage = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.order_id} - {self.user.username} - {self.company.name} - {self.execution_price}"


class CancelledOrders(AbstractOrder):
    reason = models.CharField(max_length=50, default="Default")

    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user} - {company}".format(
            user=self.user.username, company=self.company.name
        )


class CompletedOrders(AbstractOrder):
    executionprice = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    brokerage = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user} - {company}".format(
            user=self.user.username, company=self.company.name
        )


# class


def pre_save_transaction_receiver(sender, instance, *args, **kwargs):
    pass
    # amount = InvestmentRecord.objects.calculate_net_worth(instance.user)
    # instance.user_net_worth = amount

    # investment_obj , obj_created = InvestmentRecord.objects.get_or_create(

    #    user=instance.user,
    #    company=instance.company
    # )

    # if instance.mode.lower() == 'buy':
    # pass
    # instance.user.buy_stocks(instance.num_stocks, instance.price)
    # instance.company.user_buy_stocks(instance.num_stocks)
    # investment_obj.add_stocks_to_buy_escrow(instance.num_stocks) # New method added to add the order quantity to escrow - but this executes even if there is an error.
    # elif instance.mode.lower() == 'sell':
    # pass
    # instance.user.sell_stocks(instance.num_stocks, instance.price)
    # instance.company.user_sell_stocks(instance.num_stocks)
    # investment_obj.reduce_stocks(instance.num_stocks)
    # investment_obj.add_stocks_to_sell_escrow(instance.num_stocks) # New method added to add the order quantity to escrow - but this executes even if there is an error.


# pre_save.connect(pre_save_transaction_receiver, sender=Transaction)


"""def post_save_transaction_create_receiver(sender, instance, created, *args, **kwargs):
    if created:
        net_worth_list = [
            instance.user_net_worth for transaction in Transaction.objects.get_by_user(instance.user)
        ]

        instance.user.update_cv(net_worth_list)"""


# post_save.connect(post_save_transaction_create_receiver, sender=Transaction)


class TransactionSchedulerQueryset(models.query.QuerySet):
    def get_by_user(self, user):
        return self.filter(user=user)

    def get_by_company(self, company):
        return self.filter(company=company)


class TransactionSchedulerManager(models.Manager):
    def get_queryset(self):
        return TransactionQueryset(self.model, using=self._db)

    def get_by_user(self, user):
        return self.get_queryset().get_by_user(user)

    def get_by_company(self, company):
        return self.get_queryset().get_by_company(company)


class TransactionScheduler(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    num_stocks = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    mode = models.CharField(max_length=10, choices=TRANSACTION_MODES)
    first_loading_time = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = TransactionSchedulerManager()

    class Meta:
        ordering = ["-first_loading_time"]

    def __str__(self):
        return "{user}: {company} - {stocks}: {price} - {mode}".format(
            user=self.user.username,
            company=self.company.name,
            stocks=self.num_stocks,
            price=self.price,
            mode=self.mode,
        )

    def get_absolute_url(self):
        return reverse("schedules", kwargs={"username": self.user.username})

    def validate_by_price(self, price):
        if (
            self.mode == "buy"
            and price <= self.price
            and price * Decimal(self.num_stocks) <= self.user.cash
        ) or (self.mode == "sell" and price >= self.price):
            return True
        return False

    def validate_by_stocks(self):
        invested_stocks = InvestmentRecord.objects.get(
            user=self.user, company=self.company
        ).stocks
        if self.mode == "buy" or (
            self.mode == "sell" and self.num_stocks <= invested_stocks
        ):
            return True
        return False

    def perform_transaction(self, price):
        if self.validate_by_price(price) and self.validate_by_stocks():
            Transaction.objects.create(
                user=self.user,
                company=self.company,
                num_stocks=self.num_stocks,
                price=price,
                mode=self.mode,
            )
            return True
        return False


class InvestmentRecordQueryset(models.query.QuerySet):
    def get_by_user(self, user):
        return self.filter(user=user)

    def get_by_company(self, company):
        return self.filter(company=company)


class InvestmentRecordManager(models.Manager):
    def get_queryset(self):
        return InvestmentRecordQueryset(self.model, self._db)

    def get_by_user(self, user):
        return self.get_queryset().get_by_user(user=user)

    def get_by_company(self, company):
        return self.get_queryset().get_by_company(company=company)

    def calculate_net_worth(self, user):
        qs = self.get_by_user(user)
        amount = Decimal(0.00)
        for inv in qs:
            amount += Decimal(inv.stocks) * inv.company.cmp
        return amount + user.cash + user.escrow


class InvestmentRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    stocks = models.IntegerField(default=0)
    buy_escrow = models.IntegerField(default=0)
    sell_escrow = models.IntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)
    investment = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    avgprice = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    gain_loss = models.DecimalField(
        max_digits=20, decimal_places=2, default=0.00
    )  # This can actually be calculated, but including it as a field because calculations in Django templates is not ideal

    objects = InvestmentRecordManager()

    class Meta:
        unique_together = ("user", "company")

    def __str__(self):
        return self.user.username + " - " + self.company.code

    def add_stocks(self, num_stocks):
        self.stocks += num_stocks
        self.save()

    def add_stocks_to_buy_escrow(self, num_stocks):
        self.buy_escrow += num_stocks
        self.save()

    def add_stocks_to_sell_escrow(self, num_stocks):
        self.sell_escrow += num_stocks
        self.save()

    def reduce_stocks(self, num_stocks):
        if self.stocks >= num_stocks:
            self.stocks -= num_stocks
            self.save()


class News(models.Model):
    title = models.CharField(max_length=120)
    content = models.TextField()
    is_active = models.BooleanField(
        default=True
    )  # Inactive news won't appear in dashboard
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp", "-updated"]

    def __str__(self):
        return self.title


def post_save_news_create_receiver(sender, instance, created, *args, **kwargs):
    if created:
        for user in User.objects.all():
            UserNews.objects.create(
                user=user, news=instance, read=not instance.is_active
            )
    else:
        UserNews.objects.get_by_news(news=instance).update(read=not instance.is_active)


post_save.connect(post_save_news_create_receiver, sender=News)


def post_save_user_news_create_receiver(sender, instance, created, *args, **kwargs):
    if created:
        instance.news_count = News.objects.filter(is_active=True).count()
        instance.save()


post_save.connect(post_save_user_news_create_receiver, sender=User)


class UserNewsManager(models.Manager):
    def get_by_user(self, user):
        return self.get_queryset().filter(user=user)

    def get_by_news(self, news):
        return self.get_queryset().filter(news=news)


class UserNews(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    news = models.ForeignKey(News, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)

    objects = UserNewsManager()

    def __str__(self):
        return self.news.title + " - " + self.user.username


class PlayerValuations(models.Model):
    id = models.IntegerField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=50, unique=True)
    team = models.CharField(max_length=50, default="NA")
    system_valuation = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    current_form = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    mkt_qty = models.IntegerField(default=100000)


class AbstractPlayerStats(models.Model):
    name = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=200, default="NA")
    dob = models.CharField(max_length=50, default="NA")
    pob = models.CharField(max_length=50, default="NA")
    playing_role = models.CharField(max_length=50, default="NA")
    batting_style = models.CharField(max_length=50, default="NA")
    bowling_style = models.CharField(max_length=50, default="NA")
    ipl_team = models.CharField(max_length=50, default="NA")
    matches = models.IntegerField(default=0)
    batting_innings = models.IntegerField(default=0)
    notouts = models.IntegerField(default=0)
    runs = models.IntegerField(default=0)
    highest = models.CharField(max_length=10, default="0")
    batting_average = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balls_faced = models.IntegerField(default=0)
    batting_sr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    hundreds = models.IntegerField(default=0)
    fifties = models.IntegerField(default=0)
    fours = models.IntegerField(default=0)
    sixes = models.IntegerField(default=0)
    catches = models.IntegerField(default=0)
    stumpings = models.IntegerField(default=0)
    bowling_innings = models.IntegerField(default=0)
    balls_bowled = models.IntegerField(default=0)
    runs_conceded = models.IntegerField(default=0)
    wickets = models.IntegerField(default=0)
    bbi = models.CharField(max_length=10, default="0")
    bbm = models.CharField(max_length=10, default="0")
    bowling_average = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    economy = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bowling_sr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fourfers = models.IntegerField(default=0)
    fifers = models.IntegerField(default=0)
    tenfers = models.IntegerField(default=0)
    espn_link = models.URLField(max_length=200, blank=True, null=True)

    class Meta:
        abstract = True


class PlayerStatsT20Intl(AbstractPlayerStats):
    def __str__(self):
        return self.name


class PlayerStatsT20(AbstractPlayerStats):
    def __str__(self):
        return self.name


class PlayerStatsODI(AbstractPlayerStats):
    def __str__(self):
        return self.name


class PlayerStatsTest(AbstractPlayerStats):
    def __str__(self):
        return self.name


# This table will store data for the last 'n' matches for every player
# IDEA - Get rid of the Current Form table altogether. All the data we need will be available in a much better and at a much granular level in the 'Match' table
class AbstractMatch(models.Model):
    match_id = models.CharField(max_length=100, default="NA")
    name = models.CharField(max_length=50, default="NA")
    team = models.CharField(max_length=50, default="NA")
    runs = models.IntegerField(default=0)
    balls_faced = models.IntegerField(default=0)
    fours = models.IntegerField(default=0)
    sixes = models.IntegerField(default=0)
    catches = models.IntegerField(default=0)
    stumpings = models.IntegerField(default=0)
    balls_bowled = models.IntegerField(default=0)
    runs_conceded = models.IntegerField(default=0)
    wickets = models.IntegerField(default=0)

    class Meta:
        abstract = True


class CurrentForm(AbstractMatch):
    matches = models.IntegerField(default=0)
    last_match_pushed = models.IntegerField(default=0)


class Match(AbstractMatch):
    match_format = models.CharField(
        choices=FORMAT_CHOICES, max_length=20, default=FORMAT_CHOICES[0][0]
    )
    player = models.ForeignKey(Company, on_delete=models.CASCADE, default=0)
    runouts = models.IntegerField(default=0)
    dismissed = models.IntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)


class AllMatches(Match):
    match_ptr = models.OneToOneField(
        auto_created=True,
        default=1,
        on_delete=models.deletion.CASCADE,
        parent_link=True,
        primary_key=True,
        serialize=False,
        to="market.match",
    )

    def __str__(self):
        return self.player.name


class ScoreCard(models.Model):
    cricinfo_id = models.IntegerField(
        primary_key=True
    )  # This wil be Cricinfo's match id
    batting_team = models.CharField(max_length=50, default="NA")
    bowling_team = models.CharField(max_length=50, default="NA")
    batsman = models.CharField(max_length=50, default="NA")
    nonstriker = models.CharField(max_length=50, default="NA")
    bowler = models.CharField(max_length=50, default="NA")
    runs_batsman = models.IntegerField(default=0)
    runs_extras = models.IntegerField(default=0)
    extra_type = models.CharField(choices=EXTRA_TYPES, default="NONE", max_length=20)
    dismissal_type = models.CharField(
        choices=DISMISSAL_TYPES, default="NONE", max_length=20
    )
    dismissed_batsman = models.CharField(max_length=50, default="NA")
    fielder = models.CharField(max_length=50, default="NA")


class CurrentMatch(models.Model):
    match_id = models.IntegerField(default=0)  # This wil be Cricinfo's match id
    home_team = models.CharField(max_length=50, default="NA")
    away_team = models.CharField(max_length=50, default="NA")
    batting_team = models.CharField(max_length=50, default="NA")


class UpcomingMatches(models.Model):
    match_id = models.IntegerField(default=0)  # This wil be Cricinfo's match id
    home_team = models.CharField(max_length=50, default="NA")
    away_team = models.CharField(max_length=50, default="NA")
    date = models.DateTimeField(auto_now=False)


class Watch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    watch_name = models.CharField(max_length=50)
    stocks = models.ManyToManyField("market.Company", blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.watch_name}"


class BallbyBall(models.Model):
    match_id = models.CharField(max_length=500)
    innings_no = models.IntegerField(default=0)
    over_no = models.IntegerField(default=0)
    delivery_no = models.IntegerField(default=0)
    batsman = models.ForeignKey(
        "market.Company", related_name="batsman", on_delete=models.CASCADE
    )
    bowler = models.ForeignKey(
        "market.Company", related_name="bowler", on_delete=models.CASCADE
    )
    dismissed_batsman = models.ForeignKey(
        "market.Company",
        related_name="dismissed_batsman",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    fielder = models.ForeignKey(
        "market.Company",
        related_name="fielder",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    runs_batsman = models.IntegerField(default=0)
    runs_extra = models.IntegerField(default=0)
    extra_type = models.CharField(max_length=100, blank=True, null=True)
    dismissal_type = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.match_id}-innings: {self.innings_no}"
