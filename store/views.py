# views.py
from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
import requests
from .models import Order, OrderItem 



from .models import Product, CartItem, Order


# ================= HOME =================
class HomeView(View):
    template_name = 'index.html'

    def get(self, request):
        return render(request, self.template_name)


# ================= PRODUCTS API =================
# ================= PRODUCTS API =================
# ================= SIGNUP =================
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

            return JsonResponse({
                'message': 'Account created!'
            }, status=201)

        except Exception as e:
            return JsonResponse({'message': str(e)}, status=400)

    return JsonResponse({'error': 'POST required'}, status=405)


# ================= LOGIN =================
@csrf_exempt 
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            user = authenticate(
                request,
                username=data['email'],  # Email = username
                password=data['password']
            )
            
            if user is not None:
                if user.is_active:  # ← ADD THIS CHECK
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


# ================= ADD TO CART =================
@csrf_exempt
def add_to_cart(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            data = json.loads(request.body.decode('utf-8'))
            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)

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


# ================= GET CART =================
def get_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    count = CartItem.objects.filter(user=request.user).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    return JsonResponse({'count': count})


# ================= USER DASHBOARD =================
def user_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/')

    cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:6]

    return render(request, 'user_dashboard.html', {
        'cart_items': cart_items,
        'orders': orders
    })



@csrf_exempt
def get_user_orders(request):
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

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

@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_staff)
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

        # Make sure your model Product is imported
        from .models import Product  # or wherever your Product is
        product = Product.objects.create(
            name=name,
            price=price,
            category=category,
            image=image
        )
        return JsonResponse({'success': True, 'id': product.id, 'name': product.name})

    return JsonResponse({'error': 'POST required'}, status=405)

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect('home')

    import requests
from django.conf import settings

# ================= CHECKOUT SESSION =================
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
                    # NO QR - Just number + name
                    'gcash_number': '09171234567',  # ← YOUR NUMBER HERE
                    'gcash_name': 'OnlineTindahan'   # ← YOUR NAME HERE
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

from django.http import JsonResponse
from .models import Product

from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Product

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
    

# ================= AUTO ORDER CREATION =================
import time
from django.db import transaction

@login_required
@csrf_exempt
def create_order(request):
    if request.method == 'POST':
        start = time.time()
        try:
            data = json.loads(request.body)
            cart_items = data.get('cart_items', [])
            total = float(data.get('total', 0))

            # ... your data extraction ...

            # Explicit transaction + bulk creation
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
                        product_id=item_data['product_id'],
                        quantity=item_data['quantity'],
                        price=item_data['price'],
                    )
                    for item_data in cart_items
                ]
                OrderItem.objects.bulk_create(order_items)  # single query

                CartItem.objects.filter(user=request.user).delete()  # also fast

            duration = time.time() - start
            print(f"create_order took {duration:.3f}s")  # log in console

            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_number': f"ORD-{order.id:05d}",
                'message': 'Order created successfully!'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'POST only'}, status=405)