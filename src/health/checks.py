import time
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.core.cache import caches
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


def check_database():
    """Check connectivity and response time for each configured database."""
    results = {}
    for alias in settings.DATABASES:
        start = time.monotonic()
        try:
            conn = connections[alias]
            conn.ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            results[alias] = {
                "status": "up",
                "latency_ms": latency_ms,
            }
        except Exception as e:
            results[alias] = {
                "status": "down",
                "error": str(e),
            }
    return results


def check_migrations():
    """Check whether all migrations have been applied."""
    try:
        conn = connections["default"]
        executor = MigrationExecutor(conn)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = [f"{app}.{name}" for app, name in [m[0].app_label_name() for m in plan]]
            return {
                "status": "pending",
                "unapplied": pending,
            }
        return {"status": "complete"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_cache():
    """Check cache backend connectivity if django cache is configured beyond the default."""
    results = {}
    for alias in settings.CACHES:
        try:
            cache = caches[alias]
            test_key = "_health_check_test"
            cache.set(test_key, "ok", timeout=5)
            value = cache.get(test_key)
            cache.delete(test_key)
            if value == "ok":
                results[alias] = {"status": "up"}
            else:
                results[alias] = {"status": "degraded", "error": "read-back mismatch"}
        except Exception as e:
            results[alias] = {"status": "down", "error": str(e)}
    return results


def check_app():
    """Check Django application health: installed apps loaded, settings valid."""
    issues = []

    # Verify critical settings
    if settings.SECRET_KEY == "change-me-in-production":
        issues.append("SECRET_KEY is using the default value")

    if settings.DEBUG:
        issues.append("DEBUG is enabled")

    # Verify installed apps are loaded
    try:
        installed = [ac.name for ac in apps.get_app_configs()]
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # Verify critical apps are installed
    required_apps = ["accounts", "health", "rest_framework"]
    missing = [app for app in required_apps if app not in installed]
    if missing:
        issues.append(f"Missing required apps: {', '.join(missing)}")

    # Verify URL configuration loads without errors
    try:
        root_urlconf = settings.ROOT_URLCONF
        import_module(root_urlconf)
    except Exception as e:
        issues.append(f"URL configuration error: {e}")

    status = "healthy" if not issues else "warnings"
    result = {"status": status}
    if issues:
        result["warnings"] = issues
    return result
