# store/context_processors.py
from collections import OrderedDict
from .models import Team

CATEGORY_LABELS = OrderedDict([
    ("clubs", "Clubs"),
    ("nations", "Nations"),
    ("special", "Special"),
])


def cart_count(request):
    cart = request.session.get("cart", {})
    return {"cart_count": sum(cart.values())}


def nav_menu(request):
    teams = (
        Team.objects.filter(jerseys__isnull=False)
        .distinct()
        .order_by("category", "league", "order", "name")
    )

    nav = OrderedDict((key, OrderedDict()) for key in CATEGORY_LABELS)
    for team in teams:
        group = team.league or "Other"
        nav[team.category].setdefault(group, []).append(team)

    return {
        "nav_menu": [
            {"key": key, "label": label, "groups": nav.get(key, {})}
            for key, label in CATEGORY_LABELS.items()
            if nav.get(key)
        ]
    }