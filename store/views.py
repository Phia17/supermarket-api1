from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Sum
from django.db.models import F
import json
import random
import string
from .models import Product, CartItem, Order, OrderItem
from .models import Feedback
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password


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
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

@csrf_protect
@require_POST
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


@login_required
def user_dashboard(request):

    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('product')

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')[:6]

    return render(request, 'user_dashboard.html', {
        'cart_items': cart_items,
        'orders': orders,
        'user': request.user
    })

# ==================== GET USER ORDERS ====================
@login_required
@csrf_exempt
def get_user_orders(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET only'}, status=405)

    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    order_list = []

    for order in orders:
        order_list.append({
            'id': order.id,
            'order_number': order.tracking_number,
            'total': float(order.total),
            'status': order.status,
            'created_at': order.created_at.isoformat(),
        })

    return JsonResponse({'orders': order_list})


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
from .models import Product

class PublicProductList(APIView):
    def get(self, request):
        products = Product.objects.all()

        return Response([
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "image": p.image.url if p.image else "",
                "category": p.category,
                "stock": p.stock
            }
            for p in products
        ])


# ==================== CREATE CHECKOUT SESSION ====================
@login_required
@csrf_exempt
def create_checkout_session(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        total = float(data.get('total', 0))
        payment_method = data.get('payment_method', 'cod')

       
        order = Order.objects.create(
            user=request.user,
            total=total,
            customer_name="Temp",
            phone="N/A",
            address="N/A",
            payment_method=payment_method,
            status='Awaiting Payment',
        )

      
        order.tracking_number = f"ORD-{order.id:03d}"
        order.save(update_fields=['tracking_number'])

        response_data = {
            'success': True,
            'order_id': order.id,
            'order_number': order.tracking_number, 
            'message': f'Order {order.tracking_number} created!',
            'total': total,
            'payment_method': payment_method
        }

        if payment_method == 'gcash':
            response_data.update({
                'gcash_number': '09171234567',
                'gcash_name': 'OnlineTindahan'
            })
        elif payment_method == 'card':
            response_data.update({
                'card_brands': ['Visa', 'Mastercard', 'Debit'],
                'processing_time': 'Instant'
            })

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== CREATE ORDER (FAST AND CORRECT) ====================

import random

def generate_order_number():
    return f"TN-{random.randint(10000, 99999)}"

def generate_tracking_number():
    return f"ORD-{random.randint(10000, 99999)}"



@csrf_exempt
def create_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    cart_items = data.get('cart_items', [])
    total = float(data.get('total', 0))
    customer_name = data.get('customer_name', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    payment_method = data.get('payment_method', 'cod')

    if not cart_items:
        return JsonResponse({'success': False, 'error': 'Cart empty'}, status=400)

    if not customer_name or not phone or not address:
        return JsonResponse({'success': False, 'error': 'Missing customer details'}, status=400)

    try:
        with transaction.atomic():

            product_ids = [i['product_id'] for i in cart_items]
            products = Product.objects.select_for_update().filter(id__in=product_ids)

            product_map = {p.id: p for p in products}

           
            for item in cart_items:
                product = product_map.get(item['product_id'])
                qty = int(item['quantity'])

                if not product:
                    return JsonResponse({'success': False, 'error': 'Invalid product'}, status=400)

                if product.stock < qty:
                    return JsonResponse({
                        'success': False,
                        'error': f'{product.name} is out of stock'
                    }, status=400)

           
            order = Order.objects.create(
                user=request.user,
                total=total,
                customer_name=customer_name,
                phone=phone,
                address=address,
                payment_method=payment_method,
                status='Pending'
            )

            for item in cart_items:
                product = product_map[item['product_id']]
                qty = int(item['quantity'])

                product.stock -= qty
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    price=item['price']
                )
        order.tracking_number = generate_order_number()
        order.delivery_tracking = generate_tracking_number()
        order.save(update_fields=['tracking_number', 'delivery_tracking'])

        return JsonResponse({
           'success': True,
           'order_id': order.id,
           'order_number': order.tracking_number,
           'tracking_number': order.delivery_tracking
})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
# ==================== Contact Us ====================

import threading

def send_email_async(email, message):
    send_mail(
        f'Contact Us Message from {email}',
        f'Email: {email}\n\nMessage:\n{message}',
        'mrchew050@gmail.com',
        ['mrchew050@gmail.com'],
        fail_silently=True
    )

def contact_us(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        message = request.POST.get('message')

        if not email or not message:
            return JsonResponse({
                'success': False,
                'message': 'All fields are required'
            })

        Feedback.objects.create(email=email, message=message)

        threading.Thread(target=send_email_async, args=(email, message)).start()

        return JsonResponse({
            'success': True,
            'message': 'Message sent Successfully!'
        })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    })

@login_required
@csrf_exempt
def cancel_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST only'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        print("CANCEL PAYLOAD:", data)

        order_id = data.get('order_id')
        if not order_id:
            return JsonResponse({'success': False, 'message': 'Missing order_id'}, status=400)

        order = Order.objects.get(id=int(order_id), user=request.user)
        order.status = 'cancelled'
        order.save(update_fields=['status', 'updated_at'])

        return JsonResponse({'success': True, 'message': 'Order cancelled successfully!'})
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid order_id'}, status=400)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    


@csrf_exempt
def reset_password(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))
            email = data.get('email')
            new_password = data.get('new_password')

            if not email or not new_password:
                return JsonResponse({'message': 'Missing fields'}, status=400)

            try:
                user = User.objects.get(username=email)  # you use email as username
            except User.DoesNotExist:
                return JsonResponse({'message': 'User not found'}, status=404)

            user.password = make_password(new_password)
            user.save()

            return JsonResponse({'message': 'Password updated successfully'})

        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)

    return JsonResponse({'message': 'POST required'}, status=405)    


