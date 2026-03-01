from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GroupViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("groups", GroupViewSet, basename="group")

urlpatterns = [
    path("", include(router.urls)),
]
