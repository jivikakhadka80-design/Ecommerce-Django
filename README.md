# Ecommerce-Django

A Django e-commerce project with a ready-made **storefront website** (home page,
product listing with search / category filter / sorting, product pages with
reviews, cart, checkout, sign up / log in, order history) plus a **REST API**
(Django REST Framework, Djoser + SimpleJWT) and the Django admin for managing the store.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate         
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_store --demo-user    
python manage.py createsuperuser           
python manage.py runserver
```

- Website: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/ (add/edit products, collections, orders)
- REST API: http://127.0.0.1:8000/store/

`seed_store` is safe to run repeatedly. The demo customer is `demo` / `demo12345!`.

Run the tests with `python manage.py test`.

### Configuration

Settings come from environment variables (or a `.env` file next to `manage.py`;
see `.env.example`). Out of the box it runs in development mode on SQLite.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `True` | Set to `False` in production |
| `DJANGO_SECRET_KEY` | dev-only key | **Required** when `DJANGO_DEBUG=False` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts |
| `TAX_RATE` | `0.10` | Used for `price_with_tax` |
| `DB_ENGINE` | `sqlite` | `mysql` to use MySQL (`pip install mysqlclient`; set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) |

## Website pages

| URL | Page |
| --- | --- |
| `/` | Home: hero, categories, new arrivals |
| `/shop/` | All products: `?q=` search, `?collection=` category, `?sort=price_asc\|price_desc\|newest`, paginated |
| `/shop/<id>/` | Product page with stock status, add to cart, reviews, related products |
| `/cart/` | Cart: change quantity, remove items |
| `/checkout/` | Places the order (login required); stock is checked and reduced |
| `/orders/` | Your order history |
| `/account/login/`, `/account/register/` | Log in / sign up |

The cart lives in the visitor's session, so it works before logging in. Products
show a coloured placeholder tile instead of a photo (the `Product` model has no
image field); edit `shop/templates/shop/` and `shop/static/shop/css/style.css`
to restyle the site.

## API

Authentication header: `Authorization: JWT <access token>`

| Endpoint | Who | Notes |
| --- | --- | --- |
| `POST /auth/users/` | anyone | Register |
| `POST /auth/jwt/create/` | anyone | Log in, returns `access` and `refresh` |
| `GET /store/products/` | anyone | Search `?search=`, filter `?collection_id=&unit_price__gt=&unit_price__lt=`, order `?ordering=unit_price`, paginated |
| `POST/PUT/PATCH/DELETE /store/products/` | staff | A product that appears in an order cannot be deleted |
| `GET/POST /store/collections/` | read: anyone, write: staff | A collection that has products cannot be deleted |
| `GET/POST /store/products/{id}/reviews/` | anyone | Edit/delete: staff only |
| `POST /store/carts/` | anyone | Creates a cart, returns its UUID |
| `GET/DELETE /store/carts/{id}/` | anyone with the id | Cart with line totals |
| `POST/PATCH/DELETE /store/carts/{id}/items/` | anyone with the id | Adding the same product again adds to its quantity |
| `GET/PUT /store/customers/me/` | logged in | Your customer profile |
| `/store/customers/` | staff | Manage all customers |
| `POST /store/orders/` | logged in | Checkout: body `{"cart_id": "<uuid>"}`. Copies the cart into an order, reduces stock, deletes the cart. Fails with 400 on an empty cart or insufficient stock |
| `GET /store/orders/` | logged in | Customers see their own orders, staff see all |
| `PATCH/DELETE /store/orders/{id}/` | staff | e.g. `{"payment_status": "C"}` (P=pending, C=complete, F=failed) |

## Project layout

- `storefront/` - project settings and root URLs
- `store/` - products, collections, carts, orders, reviews, customers (models, API, admin)
- `core/` - custom `User` model (unique email) and Djoser serializers
- `tags/`, `likes/` - generic tagging and likes models
- `shop/` - the storefront website: views, templates (`shop/templates/shop/`), CSS, `seed_store` command
- `playground/` - scratch app with a demo view at `/playground/hello/`
