from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, StockViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("stock", StockViewSet, basename="stock")

urlpatterns = [
    path("", include(router.urls)),
]
