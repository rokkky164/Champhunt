from django.conf.urls import url
from django.urls import path
from .views import (
    MarketOverview,
    CompanyTransactionView,
    CompanyCMPChartData,
    CompanyAdminCompanyUpdateView,
    deduct_tax,
    UpdateMarketView,
    DashboardView,
    MatchCreationView,
    AllPlayersView,
    WatchList,
    UpcomingMatchPlayersView,
    OrderBookView,
    TradingDashboard,
    CompanyCMPRecordView,
    OrderCreationView,
    PlayerDetails,
    SearchNavBarView,
    GetCompanies,
    TransactShares,
    MarketPlaceOrder,
)
from .txn_threading import UpdateUserCashView
from . import views

app_name = "Market"


urlpatterns = [
    # path("dashboard", views.dashboard, name = "dashboard"),
    path("executetrades", views.executetrades, name="executetrades"),
    path("innings_change", views.innings_change, name="innings_change"),
    url(r"^match/", MatchCreationView.as_view(), name="match"),
    url(r"^dashboard/", DashboardView.as_view(), name="dashboard"),
    url(r"^allplayers/", AllPlayersView.as_view(), name="allplayers"),
    url(
        r"^upcomingmatchplayers/",
        UpcomingMatchPlayersView.as_view(),
        name="upcomingmatchplayers",
    ),
    url(r"^overview/$", MarketOverview.as_view(), name="overview"),
    url(r"^place-order/$", MarketPlaceOrder.as_view(), name="place_order"),
    path("api/data", views.getMarketData, name="data"),
    path("api/portfolio", views.getPortfolio, name="portfolio"),
    path("api/search/<str:player>", views.searchPlayer, name="searchplayer"),
    path("api/allplayers", views.getAllPlayers, name="api_allplayers"),
    url(
        r"^transact/(?P<code>\w+)$",
        CompanyTransactionView.as_view(),
        name="transaction",
    ),
    url(
        r"^admin/(?P<code>\w+)$", CompanyAdminCompanyUpdateView.as_view(), name="admin"
    ),
    url(
        r"^company/api/(?P<code>\w+)$",
        CompanyCMPChartData.as_view(),
        name="cmp_api_data",
    ),
    url(r"^tax/$", deduct_tax, name="tax"),
    url(r"^update/$", UpdateMarketView.as_view(), name="update"),
    path("search", views.search, name="search"),
    path("add/", views.match_create_view, name="match_add"),
    path("<int:pk>/", views.match_update_view, name="match_change"),
    path("ajax/load-players/", views.load_players, name="ajax_load_players"),  # AJAX
    url(r"^trading-dashboard", TradingDashboard.as_view(), name="trading_dashboard"),
    path(r"watchlist/", WatchList.as_view(), name="watchlist"),
    path(r"watchlist/<int:pk>/", WatchList.as_view(), name="watchlist"),
    url(r"^order-book", OrderBookView.as_view(), name="order_book"),
    path(
        r"company-cmp-record/<str:chart_type>/<int:company_id>/",
        CompanyCMPRecordView.as_view(),
        name="company_cmp_record",
    ),
    path(r"create-order/", OrderCreationView.as_view(), name="create_order",),
    path(
        r"player-detail/<int:player_id>/",
        PlayerDetails.as_view(),
        name="player_detail",
    ),
    path(r"player-search", SearchNavBarView.as_view(), name="player_search",),
    path(r"api/get-companies/", GetCompanies.as_view(), name="get_companies",),
    path(r"api/transact-shares/", TransactShares.as_view(), name="transact_shares",),
    path(r"update-user-cash/", UpdateUserCashView, name="update_user_cash"),
]
