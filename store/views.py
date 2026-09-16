from decimal import Decimal
import json
import uuid
import requests
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from functools import wraps
from decimal import Decimal, InvalidOperation

from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from .forms import SignupForm


from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

from .models import Jersey, JerseyVariant, Order, OrderItem, Payment, Team

SORT_OPTIONS = {
    "newest": "-created_at",
    "price_asc": "price",
    "price_desc": "-price",
}




def account_signup(request):
    if request.user.is_authenticated:
        return redirect("store:jersey_list")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("store:jersey_list")
    else:
        form = SignupForm()

    return render(request, "store/account_signup.html", {"form": form})


def account_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("store:dashboard_overview")
        return redirect("store:jersey_list")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            next_url = request.POST.get("next")
            if next_url:
                return redirect(next_url)
            if user.is_staff:
                return redirect("store:dashboard_overview")
            return redirect("store:jersey_list")
    else:
        form = AuthenticationForm()

    return render(request, "store/account_login.html", {"form": form})

@login_required(login_url="store:account_login")
def account_view(request):
    orders = (
        Order.objects.filter(customer=request.user)
        .prefetch_related("items__variant__jersey")
        .order_by("-created_at")[:10]
    )
    return render(request, "store/account.html", {
        "orders": orders,
    })


def account_logout(request):
    logout(request)
    return redirect("store:jersey_list")
def _filtered_jerseys(request, base_qs):
    qs = base_qs

    kind = request.GET.get("kind")
    if kind:
        qs = qs.filter(kind=kind)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(team__name__icontains=q) | Q(season__icontains=q)
        )

    sort = request.GET.get("sort")
    return qs.order_by(SORT_OPTIONS.get(sort, "-created_at"))


def jersey_list(request):
    jerseys = Jersey.objects.filter(is_active=True).select_related("team").prefetch_related("variants")
    jerseys = _filtered_jerseys(request, jerseys)

    featured_pool = list(
        Jersey.objects.filter(is_active=True)
        .exclude(image="")
        .exclude(image__isnull=True)
        .select_related("team")[:30]
    )
    featured_jerseys = random.sample(featured_pool, min(6, len(featured_pool))) if featured_pool else []

    context = {
        "jerseys": jerseys,
        "featured_jerseys": featured_jerseys,
        "teams": Team.objects.all(),
        "kinds": Jersey.Kind.choices,
        "selected_team": "",
        "selected_kind": request.GET.get("kind", ""),
        "selected_sort": request.GET.get("sort", ""),
        "query": request.GET.get("q", ""),
    }
    return render(request, "store/jersey_list.html", context)


def team_detail(request, slug):
    team = get_object_or_404(Team, slug=slug)
    jerseys = Jersey.objects.filter(is_active=True, team=team).select_related("team").prefetch_related("variants")
    jerseys = _filtered_jerseys(request, jerseys)

    context = {
        "jerseys": jerseys,
        "team": team,
        "teams": Team.objects.all(),
        "kinds": Jersey.Kind.choices,
        "selected_team": team.slug,
        "selected_kind": request.GET.get("kind", ""),
        "selected_sort": request.GET.get("sort", ""),
        "query": request.GET.get("q", ""),
    }
    return render(request, "store/team_detail.html", context)


def jersey_detail(request, slug):
    jersey = get_object_or_404(Jersey.objects.select_related("team").prefetch_related("variants"), slug=slug)
    return render(request, "store/jersey_detail.html", {"jersey": jersey})


# ---------- Cart (session-based) ----------

def _get_cart(session):
    return session.setdefault("cart", {})


def _cart_items(session):
    cart = _get_cart(session)
    variant_ids = [int(vid) for vid in cart.keys()]
    variants = JerseyVariant.objects.filter(id__in=variant_ids).select_related("jersey", "jersey__team")

    items = []
    total = Decimal("0")
    for variant in variants:
        qty = cart.get(str(variant.id), 0)
        if qty <= 0:
            continue
        subtotal = variant.jersey.price * qty
        total += subtotal
        items.append({"variant": variant, "quantity": qty, "subtotal": subtotal})
    return items, total


def cart_add(request):
    if request.method != "POST":
        return redirect("store:cart_view")

    variant = get_object_or_404(JerseyVariant, id=request.POST.get("variant_id"))
    cart = _get_cart(request.session)

    try:
        qty = max(1, int(request.POST.get("quantity", 1)))
    except (TypeError, ValueError):
        qty = 1

    current = cart.get(str(variant.id), 0)
    new_qty = min(current + qty, variant.stock)
    if new_qty > 0:
        cart[str(variant.id)] = new_qty
        request.session.modified = True

    return redirect("store:cart_view")


def cart_update(request, variant_id):
    variant = get_object_or_404(JerseyVariant, id=variant_id)
    cart = _get_cart(request.session)

    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1

    qty = max(1, min(qty, variant.stock))
    cart[str(variant.id)] = qty
    request.session.modified = True
    return redirect("store:cart_view")


def cart_remove(request, variant_id):
    cart = _get_cart(request.session)
    cart.pop(str(variant_id), None)
    request.session.modified = True
    return redirect("store:cart_view")


def cart_view(request):
    items, total = _cart_items(request.session)
    return render(request, "store/cart.html", {"items": items, "total": total})



AIRTEL_MONEY_CODE = "7072978"
MTN_MOMO_CODE = "0774156366"


MTN_ACCOUNT_NAME = "Cisco Sport"      # <- put the name that shows when someone sends to 0774156366
AIRTEL_ACCOUNT_NAME = "Cisco Sport"   # <- put the registered merchant/business name for the 7072978 code

MANUAL_PAYMENT_METHODS = {"airtel_money", "mtn_momo"}


@login_required(login_url="store:account_login")
def checkout(request):
    items, total = _cart_items(request.session)
    if not items:
        return redirect("store:cart_view")

    errors = []

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        if not (full_name and phone and address):
            errors.append("Please fill in your name, phone, and address.")
        else:
            order = _place_order(request, items, total, full_name, phone, address, errors)
            if order is not None:
                return redirect("store:checkout_success", order_id=order.id)

    return render(request, "store/checkout.html", {
        "items": items,
        "total": total,
        "errors": errors,
        "airtel_code": AIRTEL_MONEY_CODE,
        "mtn_code": MTN_MOMO_CODE,
        "mtn_account_name": MTN_ACCOUNT_NAME,
        "airtel_account_name": AIRTEL_ACCOUNT_NAME,
        "initial_full_name": request.user.get_full_name() or request.user.username,
        "initial_email": request.user.email,
    })


def _place_order(request, items, total, full_name, phone, address, errors):
    payment_method = request.POST.get("payment_method", "cash_on_delivery")
    payment_reference = request.POST.get("payment_reference", "").strip()

    if payment_method in MANUAL_PAYMENT_METHODS and not payment_reference:
        errors.append("Please enter the transaction reference from your payment SMS.")
        return None

    try:
        with transaction.atomic():
            variant_ids = [item["variant"].id for item in items]
            locked_variants = {
                v.id: v for v in JerseyVariant.objects.select_for_update().filter(id__in=variant_ids)
            }

            for item in items:
                variant = locked_variants[item["variant"].id]
                if variant.stock < item["quantity"]:
                    errors.append(
                        f"Only {variant.stock} left for {variant.jersey.name} ({variant.size}) — please update your cart."
                    )

            if errors:
                raise ValueError("insufficient_stock")

            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                full_name=full_name,
                phone=phone,
                email=request.POST.get("email", "").strip(),
                address=address,
                city=request.POST.get("city", "").strip(),
                payment_method=payment_method,
                status="pending",
            )
            for item in items:
                variant = locked_variants[item["variant"].id]
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item["quantity"],
                    unit_price=variant.jersey.price,
                )
                variant.stock -= item["quantity"]      # stock reduces here — already automatic
                variant.save(update_fields=["stock"])

            if payment_method in MANUAL_PAYMENT_METHODS:
                Payment.objects.create(
                    order=order,
                    provider=payment_method,
                    reference=payment_reference,
                    amount=total,
                    status="initiated",
                )
    except ValueError:
        return None

    request.session["cart"] = {}
    request.session.modified = True

    _send_whatsapp_order_alert(order)   # new — notifies her the moment an order lands

    return order


def _place_order(request, items, total, full_name, phone, address, errors):
    payment_method = request.POST.get("payment_method", "cash_on_delivery")
    payment_reference = request.POST.get("payment_reference", "").strip()

    if payment_method in MANUAL_PAYMENT_METHODS and not payment_reference:
        errors.append("Please enter the transaction reference from your payment SMS.")
        return None

    try:
        with transaction.atomic():
            variant_ids = [item["variant"].id for item in items]
            locked_variants = {
                v.id: v for v in JerseyVariant.objects.select_for_update().filter(id__in=variant_ids)
            }

            for item in items:
                variant = locked_variants[item["variant"].id]
                if variant.stock < item["quantity"]:
                    errors.append(
                        f"Only {variant.stock} left for {variant.jersey.name} ({variant.size}) — please update your cart."
                    )

            if errors:
                raise ValueError("insufficient_stock")

            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                full_name=full_name,
                phone=phone,
                email=request.POST.get("email", "").strip(),
                address=address,
                city=request.POST.get("city", "").strip(),
                payment_method=payment_method,
                status="pending",
            )
            for item in items:
                variant = locked_variants[item["variant"].id]
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item["quantity"],
                    unit_price=variant.jersey.price,
                )
                variant.stock -= item["quantity"]      # stock reduces here — already automatic
                variant.save(update_fields=["stock"])

            if payment_method in MANUAL_PAYMENT_METHODS:
                Payment.objects.create(
                    order=order,
                    provider=payment_method,
                    reference=payment_reference,
                    amount=total,
                    status="initiated",
                )
    except ValueError:
        return None

    request.session["cart"] = {}
    request.session.modified = True

    _send_whatsapp_order_alert(order)   # new — notifies her the moment an order lands

    return order


def _start_relworx_payment(order, phone, total):
    reference = f"cisco-{order.id}-{uuid.uuid4().hex[:8]}"
    payload = {
        "account_no": settings.RELWORX_ACCOUNT_NO,
        "reference": reference,
        "msisdn": phone,
        "currency": "UGX",
        "amount": str(total),
        "description": f"Order #{order.id}",
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/vnd.relworx.v2",
        "Authorization": f"Bearer {settings.RELWORX_API_KEY}",
    }

    try:
        response = requests.post(f"{RELWORX_BASE_URL}/request-payment", json=payload, headers=headers, timeout=15)
        print("RELWORX STATUS:", response.status_code)
        print("RELWORX BODY:", response.text)
        data = response.json()
    except requests.RequestException as e:
        print("RELWORX REQUEST EXCEPTION:", e)
        return False

    if not data.get("success"):
        print("RELWORX REJECTED:", data)
        return False

    Payment.objects.update_or_create(
        order=order,
        defaults={
            "provider": "relworx",
            "reference": data.get("internal_reference", reference),
            "amount": total,
            "status": "initiated",
        },
    )
    return True


def payment_pending(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/payment_pending.html", {"order": order})


def payment_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    payment = getattr(order, "payment", None)
    if not payment:
        return JsonResponse({"status": "unknown"})

    if payment.status == "successful":
        return JsonResponse({"status": "success"})
    if payment.status == "failed":
        return JsonResponse({"status": "failed"})

    headers = {
        "Accept": "application/vnd.relworx.v2",
        "Authorization": f"Bearer {settings.RELWORX_API_KEY}",
    }
    try:
        response = requests.get(
            f"{RELWORX_BASE_URL}/check-request-status",
            params={"internal_reference": payment.reference, "account_no": settings.RELWORX_ACCOUNT_NO},
            headers=headers,
            timeout=15,
        )
        data = response.json()
    except requests.RequestException:
        return JsonResponse({"status": "pending"})

    request_status = data.get("request_status") or data.get("status")

    if request_status == "success":
        payment.status = "successful"
        payment.save(update_fields=["status"])
        order.status = "paid"
        order.save(update_fields=["status"])
        request.session["cart"] = {}
        request.session.modified = True
        return JsonResponse({"status": "success"})

    if request_status == "failed":
        payment.status = "failed"
        payment.save(update_fields=["status"])
        return JsonResponse({"status": "failed"})

    return JsonResponse({"status": "pending"})


def _parse_json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}


@csrf_exempt
def relworx_webhook(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    data = request.POST if request.POST else _parse_json_body(request)
    internal_reference = data.get("internal_reference")
    status = data.get("status")

    payment = Payment.objects.filter(reference=internal_reference).select_related("order").first()
    if not payment:
        return JsonResponse({"ok": False}, status=404)

    if status == "success":
        payment.status = "successful"
        payment.save(update_fields=["status"])
        payment.order.status = "paid"
        payment.order.save(update_fields=["status"])
    elif status == "failed":
        payment.status = "failed"
        payment.save(update_fields=["status"])

    return JsonResponse({"ok": True})


def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/checkout_success.html", {"order": order})


def order_track(request):
    order = None
    error = None
    if request.method == "POST":
        order_id = request.POST.get("order_id", "").strip()
        phone = request.POST.get("phone", "").strip()
        try:
            order = Order.objects.prefetch_related("items__variant__jersey").get(id=order_id, phone=phone)
        except (Order.DoesNotExist, ValueError):
            error = "No order found with that ID and phone number."

    my_orders = None
    if request.user.is_authenticated:
        my_orders = (
            Order.objects.filter(customer=request.user)
            .prefetch_related("items__variant__jersey")
            .order_by("-created_at")
        )

    return render(request, "store/order_track.html", {
        "order": order,
        "error": error,
        "my_orders": my_orders,
    })

def _send_whatsapp_order_alert(order):
    api_key = getattr(settings, "CALLMEBOT_API_KEY", None)
    phone = getattr(settings, "ADMIN_WHATSAPP_NUMBER", None)
    if not api_key or not phone:
        return  # not configured yet — skip silently rather than break checkout

    items_summary = ", ".join(
        f"{item.quantity}x {item.variant.jersey.name} ({item.variant.size})"
        for item in order.items.all()
    )
    message = (
        f"New order #{order.id} — {order.full_name} ({order.phone})\n"
        f"Items: {items_summary}\n"
        f"Total: UGX {order.total}\n"
        f"Payment: {order.get_payment_method_display()}"
    )

    try:
        requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": phone, "text": message, "apikey": api_key},
            timeout=10,
        )
    except requests.RequestException as e:
        print("WHATSAPP ALERT FAILED:", e)


# ---------------------------------------------------------------------------
# Staff dashboard — same login as the shop, gated by is_staff
# ---------------------------------------------------------------------------

User = get_user_model()

LOW_STOCK_THRESHOLD = 3
ORDER_STATUSES = ["pending", "paid", "shipped", "delivered", "cancelled"]
REVENUE_STATUSES = ["paid", "shipped", "delivered"]


def staff_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('store:account_login')}?next={request.path}")
        if not request.user.is_staff:
            return redirect("store:jersey_list")
        return view_func(request, *args, **kwargs)
    return wrapped


@staff_required
def dashboard_overview(request):
    orders = Order.objects.all()

    status_counts = {s: orders.filter(status=s).count() for s in ORDER_STATUSES}
    revenue = sum(o.total for o in orders.filter(status__in=REVENUE_STATUSES))

    low_stock = (
        JerseyVariant.objects.select_related("jersey")
        .filter(stock__lte=LOW_STOCK_THRESHOLD)
        .order_by("stock")
    )
    recent_orders = orders.order_by("-created_at")[:8]

    context = {
        "status_counts": status_counts,
        "total_orders": orders.count(),
        "revenue": revenue,
        "low_stock": low_stock,
        "low_stock_count": low_stock.count(),
        "recent_orders": recent_orders,
        "customer_count": User.objects.filter(is_staff=False).count(),
    }
    return render(request, "store/dashboard_overview.html", context)


@staff_required
def dashboard_orders(request):
    orders = Order.objects.all().order_by("-created_at")

    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()

    if status in ORDER_STATUSES:
        orders = orders.filter(status=status)
    if q:
        orders = orders.filter(
            Q(id__icontains=q) | Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )

    return render(request, "store/dashboard_orders.html", {
        "orders": orders, "statuses": ORDER_STATUSES, "current_status": status, "q": q,
    })


@staff_required
def dashboard_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.select_related("variant", "variant__jersey").all()
    payment = Payment.objects.filter(order=order).first()

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in ORDER_STATUSES:
            order.status = new_status
            order.save(update_fields=["status"])
            return redirect("store:dashboard_order_detail", order_id=order.id)

    return render(request, "store/dashboard_order_detail.html", {
        "order": order, "items": items, "payment": payment, "statuses": ORDER_STATUSES,
    })



@staff_required
def dashboard_stock(request):
    q = request.GET.get("q", "").strip()

    if request.method == "POST":
        action = request.POST.get("action", "update_stock")

        if action == "add_jersey":
            team = get_object_or_404(Team, id=request.POST.get("team_id"))
            name = request.POST.get("name", "").strip()
            kind = request.POST.get("kind", Jersey.Kind.HOME)
            season = request.POST.get("season", "").strip()
            description = request.POST.get("description", "").strip()
            image = request.FILES.get("image")

            try:
                price = Decimal(request.POST.get("price", ""))
            except (InvalidOperation, TypeError):
                price = None

            if price is not None:
                jersey = Jersey.objects.create(
                    team=team,
                    kind=kind,
                    season=season,
                    name=name,
                    description=description,
                    price=price,
                    image=image,
                )
                for size in JerseyVariant.Size.values:
                    JerseyVariant.objects.create(jersey=jersey, size=size, stock=0)

            return redirect(f"{request.path}?q={q}" if q else request.path)

        else:  # update_stock
            variant = get_object_or_404(JerseyVariant, id=request.POST.get("variant_id"))
            try:
                variant.stock = max(0, int(request.POST.get("stock")))
                variant.save(update_fields=["stock"])
            except (TypeError, ValueError):
                pass
            return redirect(f"{request.path}?q={q}" if q else request.path)

    variants = JerseyVariant.objects.select_related("jersey", "jersey__team").order_by(
        "jersey__team__name", "jersey__name", "size"
    )
    if q:
        variants = variants.filter(Q(jersey__name__icontains=q) | Q(jersey__team__name__icontains=q))

    grouped = {}
    for v in variants:
        grouped.setdefault(v.jersey.team.name, {}).setdefault(v.jersey, []).append(v)

    team_groups = [
        {"team_name": team_name, "jerseys": [{"jersey": j, "variants": vs} for j, vs in jerseys.items()]}
        for team_name, jerseys in grouped.items()
    ]

    return render(request, "store/dashboard_stock.html", {
        "team_groups": team_groups,
        "q": q,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "teams": Team.objects.all().order_by("name"),
        "kinds": Jersey.Kind.choices,
    })



@staff_required
def dashboard_customers(request):
    q = request.GET.get("q", "").strip()
    customers = User.objects.filter(is_staff=False).annotate(order_count=Count("orders", distinct=True))

    if q:
        customers = customers.filter(Q(username__icontains=q) | Q(email__icontains=q))
    customers = customers.order_by("-date_joined")

    rows = [
        {"user": c, "order_count": c.order_count,
         "total_spent": sum(o.total for o in c.orders.filter(status__in=REVENUE_STATUSES))}
        for c in customers
    ]
    return render(request, "store/dashboard_customers.html", {"rows": rows, "q": q})