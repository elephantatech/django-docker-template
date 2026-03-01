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
