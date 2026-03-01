import pytest
from django.test import RequestFactory

from accounts.permissions import IsAdmin, IsAdminOrOperator, IsAdminOrReadOnly
from conftest import UserFactory


def _make_request(method="GET", user=None):
    factory = RequestFactory()
    fn = getattr(factory, method.lower())
    request = fn("/fake-url/")
    request.user = user
    return request


@pytest.mark.django_db
class TestIsAdmin:
    def test_admin_allowed(self, admin_user):
        request = _make_request(user=admin_user)
        assert IsAdmin().has_permission(request, None) is True

    def test_operator_denied(self, operator_user):
        request = _make_request(user=operator_user)
        assert IsAdmin().has_permission(request, None) is False

    def test_readonly_denied(self, readonly_user):
        request = _make_request(user=readonly_user)
        assert IsAdmin().has_permission(request, None) is False

    def test_no_group_denied(self):
        user = UserFactory()
        request = _make_request(user=user)
        assert IsAdmin().has_permission(request, None) is False


@pytest.mark.django_db
class TestIsAdminOrOperator:
    def test_admin_allowed(self, admin_user):
        request = _make_request(user=admin_user)
        assert IsAdminOrOperator().has_permission(request, None) is True

    def test_operator_allowed(self, operator_user):
        request = _make_request(user=operator_user)
        assert IsAdminOrOperator().has_permission(request, None) is True

    def test_readonly_denied(self, readonly_user):
        request = _make_request(user=readonly_user)
        assert IsAdminOrOperator().has_permission(request, None) is False


@pytest.mark.django_db
class TestIsAdminOrReadOnly:
    def test_admin_get(self, admin_user):
        request = _make_request("GET", admin_user)
        assert IsAdminOrReadOnly().has_permission(request, None) is True

    def test_admin_post(self, admin_user):
        request = _make_request("POST", admin_user)
        assert IsAdminOrReadOnly().has_permission(request, None) is True

    def test_operator_get(self, operator_user):
        request = _make_request("GET", operator_user)
        assert IsAdminOrReadOnly().has_permission(request, None) is True

    def test_operator_post(self, operator_user):
        request = _make_request("POST", operator_user)
        assert IsAdminOrReadOnly().has_permission(request, None) is False

    def test_readonly_get(self, readonly_user):
        request = _make_request("GET", readonly_user)
        assert IsAdminOrReadOnly().has_permission(request, None) is False

    def test_readonly_post(self, readonly_user):
        request = _make_request("POST", readonly_user)
        assert IsAdminOrReadOnly().has_permission(request, None) is False
