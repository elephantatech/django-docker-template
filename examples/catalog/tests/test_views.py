from decimal import Decimal

import pytest

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
