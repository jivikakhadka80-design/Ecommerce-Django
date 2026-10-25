from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from store.models import Cart, CartItem, Collection, Order, Product

User = get_user_model()


class ShopTestCase(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(title='Books')
        self.product = Product.objects.create(
            title='Django Guide', slug='django-guide', unit_price=Decimal('10.00'),
            inventory=5, collection=self.collection, description='Learn Django')
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345!')

    def add_to_cart(self, quantity=2):
        return self.client.post(reverse('shop:add_to_cart'), {
            'product_id': self.product.id, 'quantity': quantity})


class CatalogueTests(ShopTestCase):
    def test_home_page_shows_products(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'Django Guide')

    def test_home_page_without_products_explains_how_to_seed(self):
        Product.objects.all().delete()
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'seed_store')

    def test_search_and_collection_filter(self):
        url = reverse('shop:products')
        self.assertContains(self.client.get(url, {'q': 'django'}), 'Django Guide')
        self.assertNotContains(self.client.get(url, {'q': 'nothing-here'}), 'Django Guide')
        self.assertContains(
            self.client.get(url, {'collection': self.collection.id}), 'Django Guide')

    def test_product_detail_and_review(self):
        url = reverse('shop:product_detail', args=[self.product.pk])
        self.assertContains(self.client.get(url), 'Learn Django')
        response = self.client.post(url, {'name': 'Sam', 'description': 'Great book'})
        self.assertRedirects(response, url)
        self.assertEqual(self.product.reviews.count(), 1)


class CartAndCheckoutTests(ShopTestCase):
    def test_add_to_cart_and_view_cart(self):
        self.add_to_cart(2)
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, 2)
        self.assertContains(self.client.get(reverse('shop:cart')), '$20.00')

    def test_cart_quantity_is_capped_at_stock(self):
        self.add_to_cart(3)
        self.add_to_cart(3)
        self.assertEqual(CartItem.objects.get().quantity, 5)

    def test_update_and_remove_item(self):
        self.add_to_cart(2)
        item = CartItem.objects.get()
        self.client.post(reverse('shop:update_item'), {'item_id': item.id, 'quantity': 4})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)
        self.client.post(reverse('shop:remove_item'), {'item_id': item.id})
        self.assertEqual(CartItem.objects.count(), 0)

    def test_invalid_ids_do_not_crash(self):
        response = self.client.post(reverse('shop:add_to_cart'), {'product_id': 'abc'})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse('shop:update_item'), {'item_id': 'abc'})
        self.assertEqual(response.status_code, 302)

    def test_checkout_requires_login(self):
        self.add_to_cart()
        response = self.client.get(reverse('shop:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('shop:login'), response['Location'])

    def test_checkout_places_order(self):
        self.add_to_cart(2)
        self.client.login(username='alice', password='pass12345!')
        response = self.client.post(reverse('shop:checkout'))
        order = Order.objects.get()
        self.assertRedirects(response, reverse('shop:order_detail', args=[order.pk]))
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 3)
        self.assertEqual(Cart.objects.count(), 0)
        self.assertContains(self.client.get(reverse('shop:orders')), f'Order #{order.pk}')

    def test_empty_cart_checkout_redirects(self):
        self.client.login(username='alice', password='pass12345!')
        response = self.client.get(reverse('shop:checkout'))
        self.assertRedirects(response, reverse('shop:products'))


class AccountTests(ShopTestCase):
    def test_register_logs_the_user_in(self):
        response = self.client.post(reverse('shop:register'), {
            'username': 'newbie', 'email': 'newbie@example.com',
            'first_name': 'New', 'last_name': 'Bie',
            'password1': 'S3cure-pass-99', 'password2': 'S3cure-pass-99'})
        self.assertRedirects(response, reverse('shop:home'))
        self.assertTrue(User.objects.filter(username='newbie').exists())
        self.assertContains(self.client.get(reverse('shop:home')), 'newbie')

    def test_login_page_renders(self):
        self.assertContains(self.client.get(reverse('shop:login')), 'Log in')
