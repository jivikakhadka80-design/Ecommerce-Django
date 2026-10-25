from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from store.models import Collection, Product

CATALOGUE = {
    'Electronics': [
        ('Wireless Headphones', '59.99', 40, 'Over-ear Bluetooth headphones with 30-hour battery life and a soft carrying case.'),
        ('Smart Watch', '129.00', 25, 'Track steps, sleep and notifications with a bright always-on display.'),
        ('Portable Speaker', '39.50', 60, 'Waterproof pocket speaker with deep bass and 12 hours of playtime.'),
        ('USB-C Fast Charger', '24.99', 120, '65W compact charger for phones, tablets and laptops.'),
        ('Mechanical Keyboard', '89.00', 8, 'Hot-swappable switches, RGB backlight and a sturdy aluminium frame.'),
    ],
    'Fashion': [
        ('Classic White Sneakers', '64.90', 35, 'Minimal leather sneakers that go with everything.'),
        ('Denim Jacket', '78.00', 20, 'Mid-weight denim jacket with a relaxed modern fit.'),
        ('Cotton T-Shirt (2-pack)', '22.00', 150, 'Soft 100% cotton crew-neck tees in two colours.'),
        ('Canvas Backpack', '45.00', 4, 'Roomy 20L backpack with a padded laptop sleeve.'),
        ('Wool Scarf', '29.95', 55, 'Warm merino blend scarf, perfect for cold mornings.'),
    ],
    'Home & Kitchen': [
        ('Ceramic Mug Set', '27.00', 70, 'Set of four hand-glazed 350ml mugs, dishwasher safe.'),
        ('Non-stick Frying Pan', '34.50', 45, '28cm pan with a durable non-stick coating and cool-touch handle.'),
        ('Scented Soy Candle', '16.00', 90, 'Hand-poured soy candle with a 40-hour burn time.'),
        ('Electric Kettle', '42.00', 30, '1.7L stainless steel kettle with auto shut-off.'),
        ('Bamboo Cutting Board', '19.99', 0, 'Large reversible board with a juice groove (currently sold out).'),
    ],
    'Books': [
        ('Learn Python the Easy Way', '29.00', 50, 'A beginner-friendly guide to programming with practical projects.'),
        ('The Art of Cooking at Home', '24.50', 38, 'Over 150 simple recipes for everyday meals.'),
        ('Mindful Mornings', '14.99', 65, 'A short guide to building calm, productive routines.'),
    ],
    'Sports': [
        ('Yoga Mat', '26.00', 80, 'Non-slip 6mm mat with a carrying strap.'),
        ('Adjustable Dumbbells', '119.00', 12, 'Space-saving pair adjustable from 2 to 20 kg each.'),
        ('Insulated Water Bottle', '21.00', 100, 'Keeps drinks cold for 24 hours or hot for 12.'),
    ],
}


class Command(BaseCommand):
    help = 'Load sample collections and products (safe to run more than once).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo-user', action='store_true',
            help='Also create a demo customer (username "demo", password "demo12345!").')

    def handle(self, *args, **options):
        created_products = 0
        for collection_title, products in CATALOGUE.items():
            collection, _ = Collection.objects.get_or_create(title=collection_title)
            for title, price, inventory, description in products:
                _, created = Product.objects.get_or_create(
                    title=title, collection=collection,
                    defaults={
                        'slug': slugify(title),
                        'unit_price': Decimal(price),
                        'inventory': inventory,
                        'description': description,
                    })
                created_products += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Done: {Collection.objects.count()} collections, '
            f'{Product.objects.count()} products ({created_products} new).'))

        if options['demo_user']:
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username='demo',
                defaults={'email': 'demo@example.com', 'first_name': 'Demo', 'last_name': 'Customer'})
            if created:
                user.set_password('demo12345!')
                user.save()
                self.stdout.write(self.style.SUCCESS('Created demo user: demo / demo12345!'))
            else:
                self.stdout.write('Demo user already exists.')
