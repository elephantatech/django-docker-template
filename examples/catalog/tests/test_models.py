from decimal import Decimal

import pytest

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
