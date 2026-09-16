from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count
from django.utils.html import format_html

from .models import Team, Jersey, JerseyVariant, Order, OrderItem, Payment

User = get_user_model()


class JerseyVariantInline(admin.TabularInline):
    model = JerseyVariant
    extra = 1
    fields = ["size", "stock"]


@admin.register(Jersey)
class JerseyAdmin(admin.ModelAdmin):
    list_display = ["name", "team", "kind", "season", "price", "total_stock_display", "is_active"]
    list_filter = ["kind", "team__category", "is_active"]
    list_editable = ["price", "is_active"]
    search_fields = ["name", "team__name", "season"]
    inlines = [JerseyVariantInline]
    autocomplete_fields = ["team"]

    def total_stock_display(self, obj):
        total = obj.total_stock
        color = "#E85D5D" if total == 0 else "#3E8E5E"
        return format_html('<strong style="color:{}">{}</strong>', color, total)
    total_stock_display.short_description = "Stock"


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "league"]
    list_editable = ["category", "league"]
    list_filter = ["category"]
    search_fields = ["name", "league"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["variant", "quantity", "unit_price"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "full_name", "phone", "status_badge", "payment_method", "total_display", "created_at"]
    list_filter = ["status", "payment_method", "created_at"]
    search_fields = ["id", "full_name", "phone", "email"]
    inlines = [OrderItemInline]
    readonly_fields = ["created_at"]
    actions = ["mark_as_paid", "mark_as_shipped", "mark_as_delivered", "mark_as_cancelled"]

    def status_badge(self, obj):
        return format_html("<strong>{}</strong>", obj.get_status_display())
    status_badge.short_description = "Status"

    def total_display(self, obj):
        return f"UGX {obj.total}"
    total_display.short_description = "Total"

    @admin.action(description="Approve / mark as paid")
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status="paid")
        self.message_user(request, f"{updated} order(s) marked as paid.")

    @admin.action(description="Mark as shipped (dispatched)")
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status="shipped")
        self.message_user(request, f"{updated} order(s) marked as shipped.")

    @admin.action(description="Mark as delivered")
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status="delivered")
        self.message_user(request, f"{updated} order(s) marked as delivered.")

    @admin.action(description="Cancel order")
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} order(s) cancelled.")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "provider", "reference", "amount", "status"]
    list_filter = ["provider", "status"]
    search_fields = ["reference", "order__id"]


# ---------- Customers ----------

admin.site.unregister(User)

@admin.register(User)
class CustomerAdmin(DjangoUserAdmin):
    list_display = ["username", "email", "order_count", "total_spent", "date_joined", "is_staff"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_order_count=Count("orders", distinct=True))

    def order_count(self, obj):
        return obj._order_count
    order_count.short_description = "Orders"
    order_count.admin_order_field = "_order_count"

    def total_spent(self, obj):
        total = sum(o.total for o in obj.orders.all())
        return f"UGX {total}"
    total_spent.short_description = "Total spent"