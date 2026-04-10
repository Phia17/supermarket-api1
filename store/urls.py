from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    
    # API endpoints
    path('products/', views.PublicProductList.as_view(), name='public_products'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('get-cart/', views.get_cart, name='get_cart'),
    # store/urls.py or market/urls.py
    path('checkout/', views.create_checkout_session, name='api_checkout'),
    path('logout/', views.logout_view, name='logout'),
    path('create-order/', views.create_order, name='create_order'),
    path('create-product/', views.create_product, name='create_product'),
]