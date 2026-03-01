# Tutorial: Building a CRUD API

This tutorial walks through creating a new API app from scratch using this template. You will build a **Products & Stock** service with two related models, full CRUD endpoints, permission-based access control, and tests.

By the end you will have:

- `Product` model with name, description, price, and SKU
- `Stock` model linked to Product with quantity and warehouse location
- REST API endpoints for both resources
- Group-based permissions (Admin: full access, Operator: read/write, ReadOnly: read-only)
- Unit tests following the project conventions

## Prerequisites

Make sure you have the template running. Follow the [Getting Started](README.md#getting-started) section in the README first.

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

Replace the contents of `src/catalog/models.py`:

```python
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_entries")
    quantity = models.PositiveIntegerField(default=0)
    warehouse = models.CharField(max_length=100)
    last_restocked = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("product", "warehouse")

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse}: {self.quantity}"
```

Key points:
- `Product` has a unique `sku` field for inventory tracking
- `Stock` uses a `ForeignKey` to `Product` with `related_name="stock_entries"` so you can access stock from a product via `product.stock_entries.all()`
- `unique_together` prevents duplicate product-warehouse pairs

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

Create `src/catalog/serializers.py`:

```python
from rest_framework import serializers

from .models import Product, Stock


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ("id", "product", "quantity", "warehouse", "last_restocked")
        read_only_fields = ("id", "last_restocked")


class StockNestedSerializer(serializers.ModelSerializer):
    """Read-only serializer for nesting stock inside product responses."""

    class Meta:
        model = Stock
        fields = ("id", "quantity", "warehouse", "last_restocked")
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    stock_entries = StockNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "sku",
            "price",
            "is_active",
            "created_at",
            "updated_at",
            "stock_entries",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "description", "sku", "price", "is_active")


class ProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "description", "sku", "price", "is_active")
        read_only_fields = ("id",)
```

The pattern follows the same convention as the accounts app:
- **List serializer**: includes nested related data (read-only)
- **Create serializer**: accepts writable fields for creation
- **Update serializer**: accepts writable fields for updates

## Step 6: Create Permissions

Create `src/catalog/permissions.py`:

```python
from rest_framework.permissions import BasePermission


class IsAdminOrOperatorOrReadOnly(BasePermission):
    """
    - Admin and Operator: full access (GET, POST, PUT, PATCH, DELETE)
    - ReadOnly group: GET, HEAD, OPTIONS only
    - Unauthenticated: denied
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Read-only methods allowed for all authenticated users
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user.groups.filter(
                name__in=["Admin", "Operator", "ReadOnly"]
            ).exists()

        # Write methods require Admin or Operator
        return request.user.groups.filter(name__in=["Admin", "Operator"]).exists()
```

This follows the same `BasePermission` pattern used in `accounts/permissions.py`. You can also reuse the existing permissions from the accounts app if they fit your needs:

```python
# Reusing existing permissions
from accounts.permissions import IsAdmin, IsAdminOrOperator
```

## Step 7: Create Views

Replace the contents of `src/catalog/views.py`:

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin
from .models import Product, Stock
from .permissions import IsAdminOrOperatorOrReadOnly
from .serializers import (
    ProductCreateSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
    StockSerializer,
)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.prefetch_related("stock_entries")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return ProductCreateSerializer
        if self.action in ("update", "partial_update"):
            return ProductUpdateSerializer
        return ProductListSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        return [IsAdminOrOperatorOrReadOnly()]


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.select_related("product")
    serializer_class = StockSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        return [IsAdminOrOperatorOrReadOnly()]
```

Key points:
- `prefetch_related("stock_entries")` avoids N+1 queries when listing products
- `select_related("product")` does a JOIN for stock queries
- Destructive operations (`DELETE`) require Admin; everything else uses the read/write permission

## Step 8: Wire Up URLs

Create `src/catalog/urls.py`:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, StockViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("stock", StockViewSet, basename="stock")

urlpatterns = [
    path("", include(router.urls)),
]
```

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

Replace the contents of `src/catalog/admin.py`:

```python
from django.contrib import admin

from .models import Product, Stock


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "price", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "sku")
    inlines = [StockInline]


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "last_restocked")
    list_filter = ("warehouse",)
    search_fields = ("product__name", "warehouse")
```

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

Response:

```json
{
    "id": 1,
    "name": "Wireless Mouse",
    "description": "Ergonomic wireless mouse with USB-C receiver",
    "sku": "WM-001",
    "price": "29.99",
    "is_active": true
}
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

Create the test directory and files:

```bash
mkdir -p src/catalog/tests
touch src/catalog/tests/__init__.py
```

### Model Tests

Create `src/catalog/tests/test_models.py`:

```python
import pytest
from decimal import Decimal

from catalog.models import Product, Stock


@pytest.mark.django_db
class TestProductModel:
    def test_create_product(self):
        product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            price=Decimal("19.99"),
        )
        assert product.name == "Test Product"
        assert product.sku == "TEST-001"
        assert product.price == Decimal("19.99")
        assert product.is_active is True

    def test_str(self):
        product = Product.objects.create(name="Widget", sku="W-001", price=Decimal("5.00"))
        assert str(product) == "Widget"

    def test_unique_sku(self):
        Product.objects.create(name="First", sku="UNIQUE-001", price=Decimal("10.00"))
        with pytest.raises(Exception):
            Product.objects.create(name="Second", sku="UNIQUE-001", price=Decimal("20.00"))


@pytest.mark.django_db
class TestStockModel:
    def test_create_stock(self):
        product = Product.objects.create(name="Item", sku="ITEM-001", price=Decimal("15.00"))
        stock = Stock.objects.create(product=product, quantity=100, warehouse="Main")
        assert stock.product == product
        assert stock.quantity == 100
        assert stock.warehouse == "Main"

    def test_str(self):
        product = Product.objects.create(name="Gadget", sku="G-001", price=Decimal("9.99"))
        stock = Stock.objects.create(product=product, quantity=50, warehouse="West")
        assert str(stock) == "Gadget @ West: 50"

    def test_unique_together(self):
        product = Product.objects.create(name="Thing", sku="T-001", price=Decimal("7.00"))
        Stock.objects.create(product=product, quantity=10, warehouse="East")
        with pytest.raises(Exception):
            Stock.objects.create(product=product, quantity=20, warehouse="East")

    def test_product_relation(self):
        product = Product.objects.create(name="Box", sku="B-001", price=Decimal("3.00"))
        Stock.objects.create(product=product, quantity=10, warehouse="A")
        Stock.objects.create(product=product, quantity=20, warehouse="B")
        assert product.stock_entries.count() == 2
```

### Serializer Tests

Create `src/catalog/tests/test_serializers.py`:

```python
import pytest
from decimal import Decimal

from catalog.models import Product, Stock
from catalog.serializers import ProductListSerializer, ProductCreateSerializer, StockSerializer


@pytest.mark.django_db
class TestProductSerializers:
    def test_create_serializer_valid(self):
        data = {"name": "New", "sku": "N-001", "price": "25.00"}
        serializer = ProductCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_serializer_missing_sku(self):
        data = {"name": "No SKU", "price": "10.00"}
        serializer = ProductCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "sku" in serializer.errors

    def test_list_serializer_includes_stock(self):
        product = Product.objects.create(name="P", sku="P-001", price=Decimal("1.00"))
        Stock.objects.create(product=product, quantity=5, warehouse="WH")
        serializer = ProductListSerializer(product)
        assert len(serializer.data["stock_entries"]) == 1
        assert serializer.data["stock_entries"][0]["warehouse"] == "WH"


@pytest.mark.django_db
class TestStockSerializer:
    def test_valid_data(self):
        product = Product.objects.create(name="S", sku="S-001", price=Decimal("2.00"))
        data = {"product": product.id, "quantity": 10, "warehouse": "North"}
        serializer = StockSerializer(data=data)
        assert serializer.is_valid()

    def test_missing_product(self):
        data = {"quantity": 10, "warehouse": "North"}
        serializer = StockSerializer(data=data)
        assert not serializer.is_valid()
        assert "product" in serializer.errors
```

### View Tests

Create `src/catalog/tests/test_views.py`:

```python
import pytest
from decimal import Decimal

from catalog.models import Product, Stock


@pytest.mark.django_db
class TestProductViews:
    def test_list_products_admin(self, admin_client):
        Product.objects.create(name="A", sku="A-001", price=Decimal("1.00"))
        response = admin_client.get("/api/products/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_list_products_readonly(self, readonly_client):
        Product.objects.create(name="A", sku="A-001", price=Decimal("1.00"))
        response = readonly_client.get("/api/products/")
        assert response.status_code == 200

    def test_list_products_unauthenticated(self, api_client):
        response = api_client.get("/api/products/")
        assert response.status_code == 401

    def test_create_product_admin(self, admin_client):
        data = {"name": "New", "sku": "NEW-001", "price": "10.00"}
        response = admin_client.post("/api/products/", data)
        assert response.status_code == 201
        assert Product.objects.count() == 1

    def test_create_product_operator(self, operator_client):
        data = {"name": "New", "sku": "NEW-001", "price": "10.00"}
        response = operator_client.post("/api/products/", data)
        assert response.status_code == 201

    def test_create_product_readonly_forbidden(self, readonly_client):
        data = {"name": "New", "sku": "NEW-001", "price": "10.00"}
        response = readonly_client.post("/api/products/", data)
        assert response.status_code == 403

    def test_update_product_admin(self, admin_client):
        product = Product.objects.create(name="Old", sku="OLD-001", price=Decimal("5.00"))
        response = admin_client.patch(f"/api/products/{product.id}/", {"name": "Updated"})
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.name == "Updated"

    def test_delete_product_admin(self, admin_client):
        product = Product.objects.create(name="Del", sku="DEL-001", price=Decimal("1.00"))
        response = admin_client.delete(f"/api/products/{product.id}/")
        assert response.status_code == 204
        assert Product.objects.count() == 0

    def test_delete_product_operator_forbidden(self, operator_client):
        product = Product.objects.create(name="Del", sku="DEL-001", price=Decimal("1.00"))
        response = operator_client.delete(f"/api/products/{product.id}/")
        assert response.status_code == 403

    def test_delete_product_readonly_forbidden(self, readonly_client):
        product = Product.objects.create(name="Del", sku="DEL-001", price=Decimal("1.00"))
        response = readonly_client.delete(f"/api/products/{product.id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestStockViews:
    def setup_method(self):
        self.product = Product.objects.create(
            name="Item", sku="ITEM-001", price=Decimal("10.00")
        )

    def test_create_stock_admin(self, admin_client):
        data = {"product": self.product.id, "quantity": 50, "warehouse": "Main"}
        response = admin_client.post("/api/stock/", data)
        assert response.status_code == 201

    def test_create_stock_readonly_forbidden(self, readonly_client):
        data = {"product": self.product.id, "quantity": 50, "warehouse": "Main"}
        response = readonly_client.post("/api/stock/", data)
        assert response.status_code == 403

    def test_list_stock_readonly(self, readonly_client):
        Stock.objects.create(product=self.product, quantity=10, warehouse="WH1")
        response = readonly_client.get("/api/stock/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_update_stock_operator(self, operator_client):
        stock = Stock.objects.create(product=self.product, quantity=10, warehouse="WH1")
        response = operator_client.patch(f"/api/stock/{stock.id}/", {"quantity": 99})
        assert response.status_code == 200
        stock.refresh_from_db()
        assert stock.quantity == 99

    def test_delete_stock_admin(self, admin_client):
        stock = Stock.objects.create(product=self.product, quantity=10, warehouse="WH1")
        response = admin_client.delete(f"/api/stock/{stock.id}/")
        assert response.status_code == 204

    def test_delete_stock_operator_forbidden(self, operator_client):
        stock = Stock.objects.create(product=self.product, quantity=10, warehouse="WH1")
        response = operator_client.delete(f"/api/stock/{stock.id}/")
        assert response.status_code == 403
```

The test fixtures (`admin_client`, `operator_client`, `readonly_client`, `api_client`) are already available from the shared `conftest.py` at the project root.

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

1. **Models** in `models.py` with proper relationships and constraints
2. **Serializers** in `serializers.py` with separate list/create/update classes
3. **Permissions** in `permissions.py` extending `BasePermission`
4. **Views** in `views.py` using `ModelViewSet` with dynamic serializer/permission selection
5. **URLs** in `urls.py` using DRF's `DefaultRouter`
6. **Admin** in `admin.py` with inline editing for related models
7. **Tests** in `tests/` using the shared fixtures from `conftest.py`

Each new app you add follows this same pattern. Register it in `INSTALLED_APPS`, create migrations, wire up URLs under `api/`, and write tests using the existing fixtures.
