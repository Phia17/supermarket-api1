from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models


class Product(models.Model):
    CATEGORIES = [
        ('bath&body', 'Bath&Body'),
        ('vegetables', 'Vegetables'),
        ('snacks', 'Snacks'),
        ('meats', 'Meats'),
        ('drinks', 'Drinks'),
        ('sweets', 'Sweets'),
        ('canned', 'Canned'),
        ('seasonings', 'Seasonings'),
        ('laundry', 'Laundry'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORIES, default='bath&body')
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/%Y/%m/%d/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=10, help_text="Available stock")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def get_total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


# ==================== ORDER ====================
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('Awaiting Payment', 'Awaiting Payment'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tracking_number = models.CharField(max_length=20, blank=True, null=True)
    delivery_tracking = models.CharField(max_length=20, blank=True, null=True)

    # These are needed by create_order
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    payment_method = models.CharField(max_length=20, blank=True)

    def mark_delivered(self):
        self.status = 'delivered'
        self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"


# ==================== ORDER ITEM (OUTSIDE Order) ====================
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    class Meta:
        db_table = 'order_items'

class Feedback(models.Model):
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email        
        