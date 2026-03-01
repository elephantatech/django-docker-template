from decimal import Decimal

import pytest

from catalog.models import Product, Stock
from catalog.serializers import ProductCreateSerializer, ProductListSerializer, StockSerializer


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
