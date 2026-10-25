from django.core.exceptions import ValidationError
from django.db.models import Sum

from store.models import CartItem, Collection

from .views import CART_SESSION_KEY


def storefront(request):
    """Cart badge count and category links, available in every template."""
    count = 0
    session = getattr(request, 'session', None)
    cart_id = session.get(CART_SESSION_KEY) if session is not None else None
    if cart_id:
        try:
            count = CartItem.objects.filter(cart_id=cart_id).aggregate(
                n=Sum('quantity'))['n'] or 0
        except (ValidationError, ValueError):
            count = 0
    return {
        'cart_count': count,
        'nav_collections': Collection.objects.all()[:8],
    }
