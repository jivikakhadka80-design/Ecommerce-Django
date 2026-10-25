from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from store.models import (
    Cart, CartItem, Collection, Customer, Order, OrderItem, Product, Review)

User = get_user_model()


def make_user(username, is_staff=False):
    return User.objects.create_user(
        username=username, email=f'{username}@example.com',
        password='pass12345!', is_staff=is_staff)


class StoreAPITestCase(APITestCase):
    def setUp(self):
        self.collection = Collection.objects.create(title='Books')
        self.product = Product.objects.create(
            title='Django Guide', slug='django-guide',
            unit_price=Decimal('10.00'), inventory=5,
            collection=self.collection)
        self.user = make_user('alice')
        self.staff = make_user('boss', is_staff=True)


class ProductTests(StoreAPITestCase):
    def test_anyone_can_list_products_with_tax(self):
        response = self.client.get('/store/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data['results'][0]
        self.assertEqual(Decimal(str(result['price_with_tax'])), Decimal('11.00'))

    def test_anonymous_cannot_create_product(self):
        response = self.client.post('/store/products/', {})
        self.assertIn(response.status_code, (401, 403))

    def test_staff_can_create_product(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post('/store/products/', {
            'title': 'Python Guide', 'slug': 'python-guide',
            'unit_price': '20.00', 'inventory': 3,
            'collection': self.collection.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_product_with_orders_cannot_be_deleted(self):
        customer = Customer.objects.create(user=self.user)
        order = Order.objects.create(customer=customer)
        OrderItem.objects.create(
            order=order, product=self.product, quantity=1,
            unit_price=self.product.unit_price)
        self.client.force_authenticate(self.staff)
        response = self.client.delete(f'/store/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Product.objects.filter(pk=self.product.id).exists())

    def test_collection_with_products_cannot_be_deleted(self):
        self.client.force_authenticate(self.staff)
        response = self.client.delete(f'/store/collections/{self.collection.id}/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CartTests(StoreAPITestCase):
    def test_add_item_twice_merges_quantity(self):
        cart_id = self.client.post('/store/carts/').data['id']
        for _ in range(2):
            response = self.client.post(
                f'/store/carts/{cart_id}/items/',
                {'product_id': self.product.id, 'quantity': 2})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = CartItem.objects.get(cart_id=cart_id)
        self.assertEqual(item.quantity, 4)

    def test_unknown_product_is_rejected(self):
        cart_id = self.client.post('/store/carts/').data['id']
        response = self.client.post(
            f'/store/carts/{cart_id}/items/', {'product_id': 9999, 'quantity': 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OrderTests(StoreAPITestCase):
    def make_cart(self, quantity):
        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, product=self.product, quantity=quantity)
        return cart

    def test_anonymous_cannot_place_order(self):
        cart = self.make_cart(1)
        response = self.client.post('/store/orders/', {'cart_id': str(cart.id)})
        self.assertIn(response.status_code, (401, 403))

    def test_checkout_creates_order_and_updates_stock(self):
        cart = self.make_cart(2)
        self.client.force_authenticate(self.user)
        response = self.client.post('/store/orders/', {'cart_id': str(cart.id)})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = Order.objects.get()
        self.assertEqual(order.customer.user, self.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.get().quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 3)
        self.assertFalse(Cart.objects.filter(pk=cart.id).exists())

    def test_checkout_rejects_insufficient_stock(self):
        cart = self.make_cart(99)
        self.client.force_authenticate(self.user)
        response = self.client.post('/store/orders/', {'cart_id': str(cart.id)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.inventory, 5)

    def test_checkout_rejects_empty_cart(self):
        cart = Cart.objects.create()
        self.client.force_authenticate(self.user)
        response = self.client.post('/store/orders/', {'cart_id': str(cart.id)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customers_only_see_their_own_orders(self):
        other = make_user('bob')
        mine = Order.objects.create(
            customer=Customer.objects.create(user=self.user))
        Order.objects.create(customer=Customer.objects.create(user=other))

        self.client.force_authenticate(self.user)
        response = self.client.get('/store/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([o['id'] for o in response.data], [mine.id])

        self.client.force_authenticate(self.staff)
        self.assertEqual(len(self.client.get('/store/orders/').data), 2)

    def test_only_staff_can_update_payment_status(self):
        order = Order.objects.create(
            customer=Customer.objects.create(user=self.user))
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f'/store/orders/{order.id}/', {'payment_status': 'C'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            f'/store/orders/{order.id}/', {'payment_status': 'C'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'C')


class ReviewTests(StoreAPITestCase):
    def test_anyone_can_post_but_only_staff_can_delete(self):
        url = f'/store/products/{self.product.id}/reviews/'
        response = self.client.post(url, {'name': 'Sam', 'description': 'Great'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        review = Review.objects.get()
        detail = f'{url}{review.id}/'
        self.assertIn(self.client.delete(detail).status_code, (401, 403))

        self.client.force_authenticate(self.staff)
        self.assertEqual(
            self.client.delete(detail).status_code, status.HTTP_204_NO_CONTENT)
