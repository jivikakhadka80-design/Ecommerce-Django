from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from rest_framework import serializers

from store.models import Cart, CartItem, Collection, Order, Product
from store.serializers import CreateOrderSerializer

from .forms import RegisterForm, ReviewForm

CART_SESSION_KEY = 'cart_id'
MAX_QTY = 99


# --- helpers ----------------------------------------------------------------

def get_cart(request, create=False):
    """Return the visitor's cart (kept in the session), optionally creating it."""
    cart = None
    cart_id = request.session.get(CART_SESSION_KEY)
    if cart_id:
        try:
            cart = Cart.objects.filter(pk=cart_id).first()
        except (DjangoValidationError, ValueError):
            cart = None
    if cart is None and create:
        cart = Cart.objects.create()
        request.session[CART_SESSION_KEY] = str(cart.id)
    return cart


def cart_lines(cart):
    """Cart items with a ``line_total`` attached, plus the overall totals."""
    lines, total, count = [], 0, 0
    if cart is not None:
        for item in cart.items.select_related('product').order_by('id'):
            item.line_total = item.quantity * item.product.unit_price
            lines.append(item)
            total += item.line_total
            count += item.quantity
    return lines, total, count


def parse_id(value):
    """Return an int id, or None when the value is missing or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_quantity(value, default=1):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(quantity, MAX_QTY))


def redirect_back(request, default):
    target = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if target and url_has_allowed_host_and_scheme(
            target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect(default)


def error_messages(detail):
    """Flatten a DRF ValidationError detail into a list of strings."""
    if isinstance(detail, dict):
        return [m for value in detail.values() for m in error_messages(value)]
    if isinstance(detail, (list, tuple)):
        return [m for value in detail for m in error_messages(value)]
    return [str(detail)]


# --- catalogue --------------------------------------------------------------

def home(request):
    collections = Collection.objects.annotate(
        products_count=Count('products')).filter(products_count__gt=0)[:6]
    new_arrivals = Product.objects.select_related('collection').order_by(
        '-last_update', 'title')[:8]
    return render(request, 'shop/home.html', {
        'collections': collections,
        'new_arrivals': new_arrivals,
    })


def product_list(request):
    products = Product.objects.select_related('collection')

    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(title__icontains=query) | Q(description__icontains=query))

    current_collection = None
    collection_id = request.GET.get('collection', '')
    if collection_id.isdigit():
        current_collection = Collection.objects.filter(pk=collection_id).first()
        if current_collection:
            products = products.filter(collection=current_collection)

    sort = request.GET.get('sort', '')
    ordering = {
        'price_asc': 'unit_price',
        'price_desc': '-unit_price',
        'newest': '-last_update',
    }.get(sort, 'title')
    products = products.order_by(ordering, 'id')

    page = Paginator(products, 12).get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'shop/product_list.html', {
        'page': page,
        'query': query,
        'sort': sort,
        'current_collection': current_collection,
        'collections': Collection.objects.annotate(products_count=Count('products')),
        'querystring': params.urlencode(),
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('collection'), pk=pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            product.reviews.create(**form.cleaned_data)
            messages.success(request, 'Thanks for your review!')
            return redirect('shop:product_detail', pk=product.pk)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['name'] = request.user.get_full_name() or request.user.get_username()
        form = ReviewForm(initial=initial)

    related = Product.objects.filter(collection=product.collection) \
        .exclude(pk=product.pk).select_related('collection')[:4]

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'reviews': product.reviews.order_by('-date', '-id'),
        'review_form': form,
        'related': related,
    })



def cart_detail(request):
    lines, total, count = cart_lines(get_cart(request))
    return render(request, 'shop/cart.html', {
        'lines': lines, 'total': total, 'count': count})


@require_POST
def add_to_cart(request):
    product = get_object_or_404(Product, pk=parse_id(request.POST.get('product_id')))
    quantity = parse_quantity(request.POST.get('quantity'), default=1)
    if quantity < 1:
        quantity = 1

    cart = get_cart(request, create=True)
    item = CartItem.objects.filter(cart=cart, product=product).first()
    new_quantity = (item.quantity if item else 0) + quantity

    if product.inventory < 1:
        messages.error(request, f'Sorry, {product.title} is out of stock.')
        return redirect_back(request, 'shop:products')
    if new_quantity > product.inventory:
        new_quantity = product.inventory
        messages.warning(
            request, f'Only {product.inventory} of {product.title} available - cart adjusted.')
    else:
        messages.success(request, f'Added {product.title} to your cart.')

    if item:
        item.quantity = new_quantity
        item.save()
    else:
        CartItem.objects.create(cart=cart, product=product, quantity=new_quantity)
    return redirect_back(request, 'shop:cart')


@require_POST
def update_cart_item(request):
    cart = get_cart(request)
    item_id = parse_id(request.POST.get('item_id'))
    item = CartItem.objects.select_related('product').filter(
        pk=item_id, cart=cart).first() if cart and item_id else None
    if item is None:
        return redirect('shop:cart')

    quantity = parse_quantity(request.POST.get('quantity'), default=item.quantity)
    if quantity == 0:
        item.delete()
        messages.info(request, 'Item removed from your cart.')
    else:
        if quantity > item.product.inventory:
            quantity = max(item.product.inventory, 1)
            messages.warning(
                request, f'Only {item.product.inventory} of {item.product.title} available.')
        item.quantity = quantity
        item.save()
    return redirect('shop:cart')


@require_POST
def remove_cart_item(request):
    cart = get_cart(request)
    if cart:
        CartItem.objects.filter(cart=cart, pk=parse_id(request.POST.get('item_id'))).delete()
        messages.info(request, 'Item removed from your cart.')
    return redirect('shop:cart')



@login_required
def checkout(request):
    cart = get_cart(request)
    lines, total, count = cart_lines(cart)
    if not lines:
        messages.info(request, 'Your cart is empty.')
        return redirect('shop:products')

    if request.method == 'POST':
        serializer = CreateOrderSerializer(
            data={'cart_id': str(cart.id)},
            context={'user_id': request.user.id})
        try:
            serializer.is_valid(raise_exception=True)
            order = serializer.save()
        except serializers.ValidationError as exc:
            for message in error_messages(exc.detail):
                messages.error(request, message)
            return redirect('shop:cart')
        request.session.pop(CART_SESSION_KEY, None)
        messages.success(request, f'Thank you! Order #{order.id} has been placed.')
        return redirect('shop:order_detail', pk=order.pk)

    return render(request, 'shop/checkout.html', {
        'lines': lines, 'total': total, 'count': count})


def _with_totals(order):
    order.line_items = list(order.items.all())
    for item in order.line_items:
        item.line_total = item.quantity * item.unit_price
    order.total = sum(item.line_total for item in order.line_items)
    return order


@login_required
def order_list(request):
    orders = Order.objects.filter(customer__user=request.user) \
        .prefetch_related('items__product').order_by('-placed_at')
    return render(request, 'shop/orders.html', {
        'orders': [_with_totals(order) for order in orders]})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.filter(customer__user=request.user).prefetch_related('items__product'),
        pk=pk)
    return render(request, 'shop/order_detail.html', {'order': _with_totals(order)})



def register(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Welcome! Your account has been created.')
        return redirect('shop:home')
    return render(request, 'shop/register.html', {'form': form})
