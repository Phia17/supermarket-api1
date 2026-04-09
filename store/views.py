from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Sum
import json
import random

from .models import Product, CartItem, Order, OrderItem


class HomeView(View):
    template_name = 'index.html'

    def get(self, request):
        return render(request, self.template_name)


# ==================== SIGNUP ====================
@csrf_exempt
def signup(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password']
            )
            user.save()
            return JsonResponse({'message': 'Account created!'}, status=201)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


# ==================== LOGIN ====================
@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            user = authenticate(
                request,
                username=data['email'],
                password=data['password']
            )
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return JsonResponse({
                        'message': 'Login successful!',
                        'redirect': '/user-dashboard/',
                        'success': True
                    })
                else:
                    return JsonResponse({'message': 'Account is disabled!'}, status=400)
            else:
                return JsonResponse({'message': 'Invalid email or password!'}, status=400)
        except KeyError:
            return JsonResponse({'message': 'Email and password required!'}, status=400)
        except Exception as e:
            return JsonResponse({'message': f'Login error: {str(e)}'}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


# ==================== LOGOUT ====================
def logout_view(request):
    logout(request)
    return redirect('home')


# ==================== ADD TO CART ====================
@csrf_exempt
@login_required
def add_to_cart(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            data = json.loads(request.body.decode('utf-8'))
            product_id = data.get('product_id')
            quantity = max(1, int(data.get('quantity', 1)))

            cart_item, created = CartItem.objects.get_or_create(
                user=request.user,
                product_id=product_id,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            cart_count = CartItem.objects.filter(user=request.user).aggregate(
                total=Sum('quantity')
            )['total'] or 0

            return JsonResponse({'cart_count': cart_count})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


# ==================== GET CART ====================
def get_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    count = CartItem.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    return JsonResponse({'count': count})


# ==================== USER DASHBOARD ====================
def user_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/')

    cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:6]

    return render(request, 'user_dashboard.html', {
        'cart_items': cart_items,
        'orders': orders
    })


# ==================== GET USER ORDERS ====================
@csrf_exempt
@login_required
def get_user_orders(request):
    if request.method == 'GET':
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        order_list = []
        for order in orders:
            order_list.append({
                'id': order.id,
                'order_number': f"SM{order.id:05d}",
                'total': float(order.total),
                'status': order.status,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            })
        return JsonResponse({'orders': order_list})
    return JsonResponse({'error': 'GET required'}, status=405)


# ==================== CREATE PRODUCT (ADMIN) ====================
@login_required
@user_passes_test(lambda u: u.is_staff)
@csrf_exempt
def create_product(request):
    if request.method == 'POST':
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        name = request.POST.get('name')
        price_str = request.POST.get('price')
        category = request.POST.get('category', '').strip()
        image = request.FILES.get('image')

        if not name or not price_str:
            return JsonResponse({'error': 'Name and price are required'}, status=400)

        try:
            price = float(price_str)
        except ValueError:
            return JsonResponse({'error': 'Invalid price'}, status=400)

        product = Product.objects.create(
            name=name,
            price=price,
            category=category,
            image=image
        )
        return JsonResponse({
            'success': True,
            'id': product.id,
            'name': product.name
        })
    return JsonResponse({'error': 'POST required'}, status=405)


# ==================== PUBLIC PRODUCTS API ====================
from rest_framework.views import APIView
from rest_framework.response import Response

class PublicProductList(APIView):
    def get(self, request):
        products = Product.objects.all()
        data = []
        for p in products:
            data.append({
                "id": p.id,
                "name": p.name,
                "price": str(p.price),
                "image": p.image.url if p.image else "",
                "category": p.category,
                "stock": p.stock,
            })
        return Response(data)


# ==================== CREATE CHECKOUT SESSION ====================
@login_required
@csrf_exempt
def create_checkout_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_details = data.get('order_details', {})
            total = data.get('total', 0)
            payment_method = order_details.get('paymentMethod', 'cod')

            response_data = {
                'success': True,
                'message': f'Order #{order_details.get("orderId")} created!',
                'total': total,
                'payment_method': payment_method
            }

            if payment_method == 'gcash':
                response_data.update({
                    'gcash_number': '09171234567',   # ← your number
                    'gcash_name': 'OnlineTindahan'  # ← your name
                })
            elif payment_method == 'card':
                response_data.update({
                    'card_brands': ['Visa', 'Mastercard', 'Debit'],
                    'processing_time': 'Instant'
                })

            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'POST required'}, status=405)


# ==================== CREATE ORDER (FAST AND CORRECT) ====================

@login_required
@csrf_exempt
def create_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'Invalid JSON: {e}'}, status=400)

    cart_items = data.get('cart_items', [])
    total = data.get('total')
    customer_name = data.get('customer_name', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    payment_method = data.get('payment_method', 'cod').strip()

    # Convert total
    try:
        total = float(total) if total is not None else 0.0
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid total'}, status=400)

    if not customer_name or not phone or not address:
        return JsonResponse({'error': 'Customer name, phone, and address are required'}, status=400)

    # Validate cart items
    for item in cart_items:
        if not all(k in item for k in ('product_id', 'quantity', 'price')):
            return JsonResponse({'error': 'Invalid item (missing fields)'}, status=400)
        try:
            float(item['price'])
            int(item['quantity'])
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid price or quantity'}, status=400)

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                total=total,
                customer_name=customer_name,
                phone=phone,
                address=address,
                payment_method=payment_method,
                status='Awaiting Payment',
            )

            order_items = [
                OrderItem(
                    order=order,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)

            CartItem.objects.filter(user=request.user).delete()

        response_data = {
            'success': True,
            'order_id': order.id,
            'order_number': f"ORD-{order.id:05d}",
            'message': 'Order created successfully!',
            'total': total,
            'payment_method': payment_method,
            'created_at': order.created_at.isoformat(), 
        }

        if payment_method == 'gcash':
            response_data.update({
                'gcash_number': '09171234567',
                'gcash_name': 'OnlineTindahan'
            })
        elif payment_method == 'card':
            response_data.update({
                'card_brands': ['Visa', 'Mastercard', 'Debit']
            })

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
@csrf_exempt
def create_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'Invalid JSON: {e}'}, status=400)

    cart_items = data.get('cart_items', [])
    total = data.get('total')
    customer_name = data.get('customer_name', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    payment_method = data.get('payment_method', 'cod').strip()

    # Convert total
    try:
        total = float(total or 0)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid total'}, status=400)

    if not customer_name or not phone or not address:
        return JsonResponse({'error': 'Name, phone, and address required'}, status=400)

    # Validate cart items
    for item in cart_items:
        if not all(k in item for k in ('product_id', 'quantity', 'price')):
            return JsonResponse({'error': 'Item missing field'}, status=400)
        try:
            float(item['price'])
            int(item['quantity'])
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid price or quantity'}, status=400)

    tracking_number = 'TND' + str(random.randint(1000000000, 9999999999))
    status = 'pending'  # or 'Awaiting Payment'

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                total=total,
                customer_name=customer_name,
                phone=phone,
                address=address,
                payment_method=payment_method,
                status=status,
                tracking_number=tracking_number,
            )

            order_items = [
                OrderItem(
                    order=order,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)

            CartItem.objects.filter(user=request.user).delete()

        response_data = {
            'success': True,
            'order_id': order.id,
            'order_number': f"ORD-{order.id:005d}",
            'message': 'Order created successfully!',
            'total': total,
            'payment_method': payment_method,
        }

        if payment_method == 'gcash':
            response_data.update({
                'gcash_number': '09171234567',
                'gcash_name': 'OnlineTindahan'
            })
        elif payment_method == 'card':
            response_data.update({
                'card_brands': ['Visa', 'Mastercard', 'Debit']
            })

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    
    