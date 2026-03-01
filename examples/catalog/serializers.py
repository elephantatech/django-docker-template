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
