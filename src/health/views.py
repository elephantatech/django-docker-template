from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .checks import check_app, check_cache, check_database, check_migrations


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Comprehensive health check: database, migrations, cache, and app."""
    db = check_database()
    migrations = check_migrations()
    cache = check_cache()
    app = check_app()

    # Any database down → unhealthy
    any_db_down = any(v["status"] == "down" for v in db.values())
    # Any cache down → degraded (not fatal)
    any_cache_down = any(v["status"] == "down" for v in cache.values()) if cache else False

    if any_db_down:
        overall = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif any_cache_down or migrations.get("status") == "pending":
        overall = "degraded"
        http_status = status.HTTP_200_OK
    else:
        overall = "healthy"
        http_status = status.HTTP_200_OK

    payload = {
        "status": overall,
        "database": db,
        "migrations": migrations,
        "app": app,
    }
    if cache:
        payload["cache"] = cache

    return Response(payload, status=http_status)
