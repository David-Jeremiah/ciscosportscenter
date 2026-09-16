from django.urls import path

from . import views
from django.contrib.sitemaps.views import sitemap
from store.sitemaps import JerseySitemap, TeamSitemap, StaticViewSitemap




app_name = "store"

sitemaps = {
    "jerseys": JerseySitemap,
    "teams": TeamSitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("", views.jersey_list, name="jersey_list"),
    path("teams/<slug:slug>/", views.team_detail, name="team_detail"),
    path("jersey/<slug:slug>/", views.jersey_detail, name="jersey_detail"),

    path("cart/", views.cart_view, name="cart_view"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/update/<int:variant_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:variant_id>/", views.cart_remove, name="cart_remove"),

    path("checkout/", views.checkout, name="checkout"),
    path("checkout/success/<int:order_id>/", views.checkout_success, name="checkout_success"),
    path("orders/track/", views.order_track, name="order_track"),
    path("payments/pending/<int:order_id>/", views.payment_pending, name="payment_pending"),
    path("payments/status/<int:order_id>/", views.payment_status, name="payment_status"),
    path("payments/webhook/", views.relworx_webhook, name="relworx_webhook"),
    path("account/signup/", views.account_signup, name="account_signup"),
    path("account/login/", views.account_login, name="account_login"),
    path("account/", views.account_view, name="account_view"),
    path("account/logout/", views.account_logout, name="account_logout"),
    path("dashboard/", views.dashboard_overview, name="dashboard_overview"),
    path("dashboard/orders/", views.dashboard_orders, name="dashboard_orders"),
    path("dashboard/orders/<int:order_id>/", views.dashboard_order_detail, name="dashboard_order_detail"),
    path("dashboard/stock/", views.dashboard_stock, name="dashboard_stock"),
    path("dashboard/customers/", views.dashboard_customers, name="dashboard_customers"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
]