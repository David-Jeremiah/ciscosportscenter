from django.conf import settings
from django.db import models
from django.utils.text import slugify


# store/models.py
from django.db import models
from django.utils.text import slugify


class Team(models.Model):
    CATEGORY_CHOICES = [
        ("clubs", "Clubs"),
        ("nations", "Nations"),
        ("special", "Special"),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    league = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="teams/", blank=True, null=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="clubs",
        help_text="Controls which nav dropdown this appears under.",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category", "league", "order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Jersey(models.Model):
    class Kind(models.TextChoices):
        HOME = "home", "Home"
        AWAY = "away", "Away"
        THIRD = "third", "Third"
        GOALKEEPER = "gk", "Goalkeeper"
        RETRO = "retro", "Retro"
        VINTAGE = "vintage", "Vintage"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="jerseys")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.HOME)
    season = models.CharField(max_length=20, blank=True, help_text="e.g. 2025/26")
    name = models.CharField(max_length=150, blank=True, help_text="Override display name; auto-built if blank")
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="jerseys/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "jerseys"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{self.team.name} {self.get_kind_display()} {self.season}".strip()
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.season}")
        super().save(*args, **kwargs)

    @property
    def total_stock(self):
        return sum(v.stock for v in self.variants.all())

    def __str__(self):
        return self.name


class JerseyVariant(models.Model):
    class Size(models.TextChoices):
        XS = "XS", "XS"
        S = "S", "S"
        M = "M", "M"
        L = "L", "L"
        XL = "XL", "XL"
        XXL = "XXL", "XXL"

    jersey = models.ForeignKey(Jersey, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField(max_length=4, choices=Size.choices)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("jersey", "size")
        ordering = ["size"]

    def __str__(self):
        return f"{self.jersey.name} ({self.size})"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("cash_on_delivery", "Cash on Delivery"),
            ("mtn_momo", "MTN Mobile Money"),
            ("airtel_money", "Airtel Money"),
        ],
        default="cash_on_delivery",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        return f"Order #{self.pk} - {self.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(JerseyVariant, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.variant}"

class Payment(models.Model):
    class Provider(models.TextChoices):
        MTN_MOMO = "mtn_momo", "MTN Mobile Money"
        AIRTEL_MONEY = "airtel_money", "Airtel Money"
        CARD = "card", "Card"

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    reference = models.CharField(max_length=100, blank=True, help_text="Customer-provided transaction reference")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.INITIATED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order #{self.order_id} - {self.status}"