from django.contrib import admin
from django.utils.html import format_html
from .models import Product, CartItem, Order, OrderItem
from django.contrib import admin
from django.utils.html import format_html
from .models import Product, CartItem, Order, OrderItem, Feedback


# ==================== PRODUCT ====================
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
            return format_html('<span class="badge bg-danger">Out of Stock</span>')
        elif obj.stock < 10:
            return format_html('<span class="badge bg-warning">Low: {}</span>', obj.stock)
        return format_html('<span class="badge bg-success">In Stock: {}</span>', obj.stock)
    stock_badge.short_description = 'Stock Status'

    fields = ['name', 'category', 'price', 'stock', 'image']
    readonly_fields = ['created_at']


# ==================== ORDER ITEM INLINE ====================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']


# ==================== ORDER ADMIN (WITH ITEMS INLINE) ====================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'customer_name',
        'total',
        'status_colored',
        'created_at',
        'tracking_number'
    ]
    list_filter = ['status', 'payment_method']
    search_fields = ['user__username', 'customer_name', 'tracking_number']
    readonly_fields = ['created_at', 'updated_at', 'tracking_number']

    def status_colored(self, obj):
        color_map = {
            'pending': 'warning',
            'Awaiting Payment': 'warning',
            'shipped': 'info',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        color = color_map.get(obj.status, 'primary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'


# ==================== Contact Us ====================
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['email', 'short_message', 'created_at']
    search_fields = ['email', 'message']
    list_filter = ['created_at']
    readonly_fields = ['email', 'message', 'created_at']

    def short_message(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    short_message.short_description = 'Message'    