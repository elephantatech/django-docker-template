from unittest.mock import MagicMock, patch

import pytest
from django.test.utils import override_settings
from rest_framework import status

from health.checks import check_app, check_cache, check_database, check_migrations

HEALTH_URL = "/api/health/"


# ── Endpoint integration tests ────────────────────────────


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_healthy_response(self, api_client):
        response = api_client.get(HEALTH_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"

    def test_no_auth_required(self, api_client):
        response = api_client.get(HEALTH_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_response_contains_all_sections(self, api_client):
        response = api_client.get(HEALTH_URL)
        assert "database" in response.data
        assert "migrations" in response.data
        assert "app" in response.data

    def test_unhealthy_when_db_down(self, api_client):
        with patch("health.checks.connections") as mock_conns:
            mock_conn = MagicMock()
            mock_conn.ensure_connection.side_effect = Exception("connection refused")
            mock_conns.__getitem__.return_value = mock_conn
            response = api_client.get(HEALTH_URL)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "unhealthy"

    def test_degraded_when_cache_down(self, api_client):
        with patch("health.checks.caches") as mock_caches:
            mock_cache = MagicMock()
            mock_cache.set.side_effect = Exception("cache unavailable")
            mock_caches.__iter__ = MagicMock(return_value=iter(["default"]))
            mock_caches.__getitem__.return_value = mock_cache
            with override_settings(
                CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
            ):
                response = api_client.get(HEALTH_URL)
        # Cache failure is degraded, not unhealthy
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "degraded"

    def test_degraded_when_migrations_pending(self, api_client):
        with patch("health.checks.MigrationExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_migration = MagicMock()
            mock_migration.app_label_name.return_value = ("accounts", "0002_fake")
            mock_executor.migration_plan.return_value = [(mock_migration,)]
            mock_executor.loader.graph.leaf_nodes.return_value = []
            mock_executor_cls.return_value = mock_executor
            response = api_client.get(HEALTH_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "degraded"
        assert response.data["migrations"]["status"] == "pending"


# ── Unit tests for individual checks ──────────────────────


@pytest.mark.django_db
class TestCheckDatabase:
    def test_returns_up_for_default(self):
        result = check_database()
        assert "default" in result
        assert result["default"]["status"] == "up"
        assert "latency_ms" in result["default"]

    def test_returns_down_on_failure(self):
        with patch("health.checks.connections") as mock_conns:
            mock_conn = MagicMock()
            mock_conn.ensure_connection.side_effect = Exception("refused")
            mock_conns.__getitem__.return_value = mock_conn
            result = check_database()
        assert result["default"]["status"] == "down"
        assert "error" in result["default"]

    def test_latency_is_numeric(self):
        result = check_database()
        assert isinstance(result["default"]["latency_ms"], float)


@pytest.mark.django_db
class TestCheckMigrations:
    def test_complete_when_all_applied(self):
        result = check_migrations()
        assert result["status"] == "complete"

    def test_pending_when_unapplied(self):
        with patch("health.checks.MigrationExecutor") as mock_cls:
            mock_executor = MagicMock()
            mock_migration = MagicMock()
            mock_migration.app_label_name.return_value = ("accounts", "0099_future")
            mock_executor.migration_plan.return_value = [(mock_migration,)]
            mock_executor.loader.graph.leaf_nodes.return_value = []
            mock_cls.return_value = mock_executor
            result = check_migrations()
        assert result["status"] == "pending"
        assert "accounts.0099_future" in result["unapplied"]

    def test_error_on_exception(self):
        with patch("health.checks.MigrationExecutor", side_effect=Exception("db locked")):
            result = check_migrations()
        assert result["status"] == "error"
        assert "db locked" in result["error"]


class TestCheckCache:
    def test_no_caches_returns_empty(self):
        # Default Django settings use LocMemCache; check it works
        result = check_cache()
        assert isinstance(result, dict)

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_locmem_cache_up(self):
        result = check_cache()
        assert result["default"]["status"] == "up"

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_cache_down_on_failure(self):
        with patch("health.checks.caches") as mock_caches:
            mock_cache = MagicMock()
            mock_cache.set.side_effect = ConnectionError("cache down")
            mock_caches.__iter__ = MagicMock(return_value=iter(["default"]))
            mock_caches.__getitem__.return_value = mock_cache
            result = check_cache()
        assert result["default"]["status"] == "down"
        assert "cache down" in result["default"]["error"]


class TestCheckApp:
    def test_healthy_app(self):
        result = check_app()
        assert result["status"] in ("healthy", "warnings")

    @override_settings(SECRET_KEY="change-me-in-production", DEBUG=False)
    def test_warns_on_default_secret_key(self):
        result = check_app()
        assert result["status"] == "warnings"
        assert any("SECRET_KEY" in w for w in result["warnings"])

    @override_settings(DEBUG=True)
    def test_warns_on_debug_enabled(self):
        result = check_app()
        assert result["status"] == "warnings"
        assert any("DEBUG" in w for w in result["warnings"])

    def test_verifies_required_apps(self):
        result = check_app()
        # Should not report missing required apps since they're installed
        if "warnings" in result:
            assert not any("Missing required apps" in w for w in result["warnings"])
