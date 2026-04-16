from django.urls import path
from . import views
from django.urls import path
from .views import create_order, cancel_order

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('products/', views.PublicProductList.as_view(), name='public_products'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('get-cart/', views.get_cart, name='get_cart'),
    path('checkout/', views.create_checkout_session, name='api_checkout'),
    path('logout/', views.logout_view, name='logout'),
    path('create-order/', views.create_order, name='create_order'),
    path('create-product/', views.create_product, name='create_product'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('cancel-order/', views.cancel_order, name='cancel_order'),
    path('reset-password/', views.reset_password, name='reset_password'),
]