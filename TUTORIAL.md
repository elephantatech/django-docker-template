# Tutorial: Building a CRUD API

This tutorial walks through creating a new API app from scratch using this template. You will build a **Products & Stock** service with two related models, full CRUD endpoints, permission-based access control, and tests.

All example source files are in the [`examples/catalog/`](examples/catalog/) directory. Each step below references the file you need to copy into your app.

By the end you will have:

- `Product` model with name, description, price, and SKU
- `Stock` model linked to Product with quantity and warehouse location
- REST API endpoints for both resources
- Group-based permissions (Admin: full access, Operator: read/write, ReadOnly: read-only)
- Unit tests following the project conventions

## Prerequisites

Make sure you have the template running. Follow the [Getting Started](README.md#getting-started) section in the README first.

## Example File Structure

```
examples/catalog/
├── apps.py                  # App configuration
├── models.py                # Product and Stock models
├── serializers.py           # List, Create, Update, Nested serializers
├── permissions.py           # IsAdminOrOperatorOrReadOnly permission
├── views.py                 # ProductViewSet, StockViewSet
├── urls.py                  # DRF router registration
├── admin.py                 # Django admin with inline editing
└── tests/
    ├── __init__.py
    ├── test_models.py       # Model unit tests
    ├── test_serializers.py  # Serializer unit tests
    └── test_views.py        # View + permission tests
```

## Step 1: Create the Django App

From the `src/` directory, create a new Django app:

```bash
# Docker Compose
docker compose exec web /app/.venv/bin/python manage.py startapp catalog

# Local
cd src
uv run python manage.py startapp catalog
```

This creates the `src/catalog/` directory with the default Django app files.

## Step 2: Register the App

Add the app to `INSTALLED_APPS` in `src/main/settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    # Local
    "accounts.apps.AccountsConfig",
    "health.apps.HealthConfig",
    "catalog.apps.CatalogConfig",  # Add this line
]
```

## Step 3: Define Models

Copy [`examples/catalog/models.py`](examples/catalog/models.py) to `src/catalog/models.py`.

This defines two models:

- **Product** — name, description, SKU (unique), price, active flag, timestamps
- **Stock** — foreign key to Product, quantity, warehouse location, last restocked timestamp

Key points:
- `Stock` uses `ForeignKey` to `Product` with `related_name="stock_entries"` so you can access stock from a product via `product.stock_entries.all()`
- `unique_together` on `(product, warehouse)` prevents duplicate entries for the same product in the same warehouse

## Step 4: Create and Run Migrations

```bash
# Docker Compose
docker compose exec web /app/.venv/bin/python manage.py makemigrations catalog
docker compose exec web /app/.venv/bin/python manage.py migrate

# Local
uv run python manage.py makemigrations catalog
uv run python manage.py migrate
```

## Step 5: Create Serializers

Copy [`examples/catalog/serializers.py`](examples/catalog/serializers.py) to `src/catalog/serializers.py`.

The pattern follows the same convention as the accounts app:

- **`ProductListSerializer`** — includes nested `StockNestedSerializer` for read-only display
- **`ProductCreateSerializer`** — accepts writable fields for creation
- **`ProductUpdateSerializer`** — accepts writable fields for updates
- **`StockSerializer`** — standard CRUD serializer for stock entries
- **`StockNestedSerializer`** — read-only, used when nesting stock inside product responses

## Step 6: Create Permissions

Copy [`examples/catalog/permissions.py`](examples/catalog/permissions.py) to `src/catalog/permissions.py`.

This defines `IsAdminOrOperatorOrReadOnly`:

- **Admin and Operator**: full access (GET, POST, PUT, PATCH, DELETE)
- **ReadOnly group**: GET, HEAD, OPTIONS only
- **Unauthenticated**: denied

This follows the same `BasePermission` pattern used in `accounts/permissions.py`. You can also reuse the existing permissions from the accounts app if they fit your needs:

```python
from accounts.permissions import IsAdmin, IsAdminOrOperator
```

## Step 7: Create Views

Copy [`examples/catalog/views.py`](examples/catalog/views.py) to `src/catalog/views.py`.

This defines two viewsets:

- **`ProductViewSet`** — uses `prefetch_related("stock_entries")` to avoid N+1 queries, switches serializer class based on action, restricts DELETE to Admin only
- **`StockViewSet`** — uses `select_related("product")` for efficient JOINs, restricts DELETE to Admin only

## Step 8: Wire Up URLs

Copy [`examples/catalog/urls.py`](examples/catalog/urls.py) to `src/catalog/urls.py`.

Then add the catalog URLs to the root URL config in `src/main/urls.py`:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT authentication
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Apps
    path("api/", include("accounts.urls")),
    path("api/", include("catalog.urls")),  # Add this line
    path("api/health/", include("health.urls")),
    # Prometheus metrics
    path("", include("django_prometheus.urls")),
]
```

## Step 9: Register in Django Admin

Copy [`examples/catalog/admin.py`](examples/catalog/admin.py) to `src/catalog/admin.py`.

This registers both models in the Django admin with:

- **ProductAdmin** — list display with SKU and price, search by name/SKU, inline Stock editing
- **StockAdmin** — list display with warehouse and quantity, filter by warehouse

## Step 10: Update ruff Config

Add the new app to the known first-party imports in `src/pyproject.toml`:

```toml
[tool.ruff.lint.isort]
known-first-party = ["main", "accounts", "health", "logging_utils", "catalog"]
```

## Step 11: Test the API

Restart the services and run migrations:

```bash
# Docker Compose
docker compose up --build -d
docker compose exec web /app/.venv/bin/python manage.py migrate

# Local
uv run python manage.py migrate
uv run python manage.py runserver
```

Get a JWT token:

```bash
curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}' | python -m json.tool
```

Save the access token:

```bash
TOKEN="<paste_access_token_here>"
```

### Create a Product

```bash
curl -s -X POST http://localhost:8000/api/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Mouse",
    "description": "Ergonomic wireless mouse with USB-C receiver",
    "sku": "WM-001",
    "price": "29.99"
  }' | python -m json.tool
```

### Add Stock for the Product

```bash
curl -s -X POST http://localhost:8000/api/stock/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product": 1,
    "quantity": 150,
    "warehouse": "US-East"
  }' | python -m json.tool
```

```bash
curl -s -X POST http://localhost:8000/api/stock/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product": 1,
    "quantity": 75,
    "warehouse": "US-West"
  }' | python -m json.tool
```

### List Products (with nested stock)

```bash
curl -s http://localhost:8000/api/products/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Response:

```json
[
    {
        "id": 1,
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with USB-C receiver",
        "sku": "WM-001",
        "price": "29.99",
        "is_active": true,
        "created_at": "2026-03-01T12:00:00Z",
        "updated_at": "2026-03-01T12:00:00Z",
        "stock_entries": [
            {
                "id": 1,
                "quantity": 150,
                "warehouse": "US-East",
                "last_restocked": "2026-03-01T12:00:00Z"
            },
            {
                "id": 2,
                "quantity": 75,
                "warehouse": "US-West",
                "last_restocked": "2026-03-01T12:01:00Z"
            }
        ]
    }
]
```

### Update Stock Quantity

```bash
curl -s -X PATCH http://localhost:8000/api/stock/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 200}' | python -m json.tool
```

### Delete a Product (Admin only)

```bash
curl -s -X DELETE http://localhost:8000/api/products/1/ \
  -H "Authorization: Bearer $TOKEN"
```

## Step 12: Write Tests

Copy the test files from [`examples/catalog/tests/`](examples/catalog/tests/) to `src/catalog/tests/`:

```bash
mkdir -p src/catalog/tests
cp examples/catalog/tests/__init__.py src/catalog/tests/
cp examples/catalog/tests/test_models.py src/catalog/tests/
cp examples/catalog/tests/test_serializers.py src/catalog/tests/
cp examples/catalog/tests/test_views.py src/catalog/tests/
```

The test files include:

- [`test_models.py`](examples/catalog/tests/test_models.py) — 7 tests covering Product creation, string representation, unique SKU constraint, Stock creation, string representation, unique_together constraint, and ForeignKey relations
- [`test_serializers.py`](examples/catalog/tests/test_serializers.py) — 5 tests covering serializer validation, missing required fields, and nested stock serialization
- [`test_views.py`](examples/catalog/tests/test_views.py) — 17 tests covering CRUD operations and permission checks for Admin, Operator, ReadOnly, and unauthenticated users across both Product and Stock endpoints

The test fixtures (`admin_client`, `operator_client`, `readonly_client`, `api_client`) are already available from the shared `conftest.py` at the project root.

Run the tests:

```bash
# Local
cd src
uv run pytest catalog/tests/ -v

# Docker Compose
docker compose run --rm -e DATABASE_URL=sqlite:///test.db \
  web /app/.venv/bin/pytest catalog/tests/ -v
```

## API Reference

Here is the full endpoint and permission matrix for the catalog app:

### Products

| Method | Endpoint | Admin | Operator | ReadOnly |
|---|---|---|---|---|
| GET | `/api/products/` | All | All | All |
| POST | `/api/products/` | Create | Create | 403 |
| GET | `/api/products/{id}/` | Detail | Detail | Detail |
| PUT/PATCH | `/api/products/{id}/` | Update | Update | 403 |
| DELETE | `/api/products/{id}/` | Delete | 403 | 403 |

### Stock

| Method | Endpoint | Admin | Operator | ReadOnly |
|---|---|---|---|---|
| GET | `/api/stock/` | All | All | All |
| POST | `/api/stock/` | Create | Create | 403 |
| GET | `/api/stock/{id}/` | Detail | Detail | Detail |
| PUT/PATCH | `/api/stock/{id}/` | Update | Update | 403 |
| DELETE | `/api/stock/{id}/` | Delete | 403 | 403 |

## Summary

You have built a complete CRUD API by following the template conventions:

1. **Models** — [`models.py`](examples/catalog/models.py) with proper relationships and constraints
2. **Serializers** — [`serializers.py`](examples/catalog/serializers.py) with separate list/create/update classes
3. **Permissions** — [`permissions.py`](examples/catalog/permissions.py) extending `BasePermission`
4. **Views** — [`views.py`](examples/catalog/views.py) using `ModelViewSet` with dynamic serializer/permission selection
5. **URLs** — [`urls.py`](examples/catalog/urls.py) using DRF's `DefaultRouter`
6. **Admin** — [`admin.py`](examples/catalog/admin.py) with inline editing for related models
7. **Tests** — [`tests/`](examples/catalog/tests/) using the shared fixtures from `conftest.py`

Each new app you add follows this same pattern. Register it in `INSTALLED_APPS`, create migrations, wire up URLs under `api/`, and write tests using the existing fixtures.
