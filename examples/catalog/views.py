from rest_framework import viewsets

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
