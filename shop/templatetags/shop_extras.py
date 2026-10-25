from django import template

register = template.Library()


@register.filter
def ph_class(value):
    """Pick one of six placeholder colour classes for a product thumbnail."""
    try:
        return f'ph-{int(value) % 6}'
    except (TypeError, ValueError):
        return 'ph-0'
