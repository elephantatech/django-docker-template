from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow access only to users in the Admin group."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name="Admin").exists()
        )


class IsAdminOrOperator(BasePermission):
    """Allow access to users in the Admin or Operator group."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name__in=["Admin", "Operator"]).exists()
        )


class IsAdminOrReadOnly(BasePermission):
    """Admin gets full access; others get read-only (GET, HEAD, OPTIONS)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user.groups.filter(name__in=["Admin", "Operator"]).exists()
        return request.user.groups.filter(name="Admin").exists()
