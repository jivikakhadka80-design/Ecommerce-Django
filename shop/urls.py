from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.product_list, name='products'),
    path('shop/<int:pk>/', views.product_detail, name='product_detail'),

    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart_item, name='update_item'),
    path('cart/remove/', views.remove_cart_item, name='remove_item'),

    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='orders'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),

    path('account/login/', auth_views.LoginView.as_view(
        template_name='shop/login.html', redirect_authenticated_user=True), name='login'),
    path('account/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('account/register/', views.register, name='register'),
]
