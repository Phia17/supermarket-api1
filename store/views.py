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



from .models import Product, CartItem, Order


# ================= HOME =================
class HomeView(View):
    template_name = 'index.html'

    def get(self, request):
        return render(request, self.template_name)


# ================= PRODUCTS API =================
class PublicProductList(View):
    def get(self, request):  # simplified over ListView
        products = Product.objects.values(
            'id', 'name', 'price', 'image', 'category'
        )
        return JsonResponse(list(products), safe=False)


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
            # Get total from the frontend
            amount = data.get('total', 0) 
            # PayMongo expects amount in centavos (e.g., 200.00 PHP = 20000)
            amount_in_centavos = int(float(amount) * 100)

            url = "https://api.paymongo.com/v1/checkout_sessions"
            
            payload = {
                "data": {
                    "attributes": {
                        "send_email_receipt": True,
                        "show_description": True,
                        "show_line_items": True,
                        "description": "SuperMart Grocery Order",
                        "line_items": [{
                            "currency": "PHP",
                            "amount": amount_in_centavos,
                            "description": "Grocery Items",
                            "quantity": 1,
                            "name": "SuperMart Checkout"
                        }],
                        "payment_method_types": ["gcash", "card"],
                        "success_url": "http://127.0.0.1:8000/user-dashboard/",
                        "cancel_url": "http://127.0.0.1:8000/user-dashboard/"
                    }
                }
            }

            # PayMongo uses Basic Auth. We pass the Secret Key as the username.
            import base64
            secret_key = "sk_live_YVmnF5uN5BgdYta7xcxnPuiT" # Replace with sk_test for testing!
            auth_str = f"{secret_key}:"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Basic {encoded_auth}"
            }

            response = requests.post(url, json=payload, headers=headers)
            res_data = response.json()

            # Debugging: check your terminal if the request fails
            print("PayMongo Response:", res_data)

            if response.status_code == 200:
                checkout_url = res_data['data']['attributes']['checkout_url']
                return JsonResponse({'checkout_url': checkout_url})
            else:
                # Capture the specific error message from PayMongo
                error_detail = res_data.get('errors', [{}])[0].get('detail', 'Payment Gateway Error')
                return JsonResponse({'error': error_detail}, status=400)

        except Exception as e:
            return JsonResponse({'error': f"Server Error: {str(e)}"}, status=500)

    return JsonResponse({'error': 'POST required'}, status=405)