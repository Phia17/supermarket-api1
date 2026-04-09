from django.contrib import admin
from django.utils.html import format_html
from .models import Product, CartItem, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'stock_badge', 'category_display', 'image_preview', 'created_at']
    list_editable = ['price', 'stock']
    list_filter = ['category']
    search_fields = ['name']
    list_per_page = 25
    ordering = ['-created_at']
    
    def category_display(self, obj):
        return dict(Product.CATEGORIES).get(obj.category, obj.category)  
    category_display.short_description = 'Category'
    
    def image_preview(self, obj):
        if obj.image and obj.image.url: 
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="50" height="50" style="border-radius: 5px; object-fit: cover;" /></a>',
                obj.image.url, obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Image'
    
    def stock_badge(self, obj):
        if obj.stock == 0:
            return format_html('<span class="badge bg-danger">Out of Stock</span>')  # ✅ bg-danger
        elif obj.stock < 10:
            return format_html('<span class="badge bg-warning">Low: {}</span>', obj.stock)
        return format_html('<span class="badge bg-success">In Stock: {}</span>', obj.stock)
    stock_badge.short_description = 'Stock Status'
    
    fields = ['name', 'category', 'price', 'stock', 'image']
    readonly_fields = ['created_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'quantity', 'total_price']
    search_fields = ['product__name', 'user__username']
    list_per_page = 50
    
    def total_price(self, obj):
        return f"₱{obj.get_total_price():.2f}"
    total_price.short_description = 'Total'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total', 'status', 'created_at', 'tracking_number']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'tracking_number']
    list_per_page = 25
    readonly_fields = ['created_at', 'updated_at']