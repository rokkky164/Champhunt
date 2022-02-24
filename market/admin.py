from django.contrib import admin
from .models import (
    Company,
    InvestmentRecord,
    CompanyCMPRecord,
    Transaction,
    News,
    UserNews,
    TransactionScheduler,
    Buybook,
    Sellbook,
    Buystage,
    Sellstage,
    PlayerValuations,
    Match,
    UpcomingMatches,
    CurrentMatch,
    CompletedOrders,
    Watch,
    Order,
    BallbyBall,
)


class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "cmp", "quantity")
    search_fields = ("code", "name")
    ordering = ("id", "name")

    class Meta:
        model = Company


admin.site.register(Company, CompanyAdmin)


class CompletedOrdersAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_id",
        "user",
        "company",
        "mode",
        "num_stocks",
        "orderprice",
        "executionprice",
        "brokerage",
        "first_loading_time",
        "updated",
        "status",
    )
    search_fields = ("order_id", "user", "company", "mode")
    ordering = (
        "order_id",
        "user",
        "company",
        "mode",
        "num_stocks",
        "orderprice",
        "executionprice",
        "brokerage",
        "first_loading_time",
        "updated",
        "status",
    )

    class Meta:
        model = CompletedOrders


admin.site.register(CompletedOrders, CompletedOrdersAdmin)


class InvestmentRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "stocks")
    search_fields = ["user", "company"]
    ordering = ("user", "company")

    class Meta:
        model = InvestmentRecord


admin.site.register(InvestmentRecord, InvestmentRecordAdmin)


class CompanyCMPRecordAdmin(admin.ModelAdmin):
    list_display = ("company", "cmp", "timestamp")
    search_fields = ["company"]
    ordering = ("company", "timestamp")

    class Meta:
        model = CompanyCMPRecord


admin.site.register(CompanyCMPRecord, CompanyCMPRecordAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "num_stocks", "mode", "first_loading_time")
    search_fields = ["user", "company"]
    ordering = ("user", "company", "mode", "first_loading_time")

    class Meta:
        model = Transaction


admin.site.register(Transaction, TransactionAdmin)

# Registering Buybook, Sellbook, Buystage, Sellstage - Pranay


class BuybookAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "num_stocks", "first_loading_time")
    search_fields = ["user", "company"]
    ordering = ("user", "company", "first_loading_time")

    class Meta:
        model = Transaction


admin.site.register(Buybook, BuybookAdmin)


class SellbookAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "num_stocks", "first_loading_time")
    search_fields = ["user", "company"]
    ordering = ("user", "company", "first_loading_time")

    class Meta:
        model = Transaction


admin.site.register(Sellbook, SellbookAdmin)


class BuystageAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "num_stocks", "first_loading_time")
    search_fields = ["user", "company"]
    ordering = ("user", "company", "first_loading_time")

    class Meta:
        model = Transaction


admin.site.register(Buystage, BuystageAdmin)


class SellstageAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "num_stocks", "first_loading_time")
    search_fields = ["user", "company"]
    ordering = ("user", "company", "first_loading_time")

    class Meta:
        model = Transaction


admin.site.register(Sellstage, SellstageAdmin)

admin.site.register(PlayerValuations)


class MatchAdmin(admin.ModelAdmin):
    list_display = ("match_id", "name", "team", "updated")
    search_fields = ["match_id", "name", "team"]
    ordering = ("updated", "match_id")

    class Meta:
        model = Match


admin.site.register(Match, MatchAdmin)

# /Pranay


class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active")
    search_fields = ["title"]
    ordering = ("title", "is_active")

    class Meta:
        model = News


admin.site.register(News, NewsAdmin)


class UserNewsAdmin(admin.ModelAdmin):
    list_display = ("user", "news", "read")
    search_fields = ["user", "news"]
    ordering = ("user", "news", "read")

    class Meta:
        model = UserNews


admin.site.register(UserNews, UserNewsAdmin)


class TransactionSchedulerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company",
        "num_stocks",
        "price",
        "mode",
        "first_loading_time",
    )
    search_fields = ["user", "company", "mode"]
    ordering = ("user", "company", "mode", "price", "first_loading_time")

    class Meta:
        model = TransactionScheduler


admin.site.register(TransactionScheduler, TransactionSchedulerAdmin)

admin.site.register(CurrentMatch)
admin.site.register(UpcomingMatches)
admin.site.register(Watch)
admin.site.register(Order)
admin.site.register(BallbyBall)
