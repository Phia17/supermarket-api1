from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Product(models.Model):
    CATEGORIES = [
        ('fruits', 'Fruits'),
        ('vegetables', 'Vegetables'),
        ('dairy', 'Dairy'),
        ('meats', 'Meats'),
        ('drinks', 'Drinks'),
        ('sweets', 'Sweets'),
    ]
    
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.CharField(max_length=500)
    category = models.CharField(max_length=50, choices=CATEGORIES)
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

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tracking_number = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"Order {self.id} - {self.user.username}"
