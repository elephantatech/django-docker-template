import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from conftest import UserFactory

User = get_user_model()

LIST_URL = "/api/users/"
ME_URL = "/api/users/me/"
CHANGE_PASSWORD_URL = "/api/users/change-password/"


def detail_url(user_id):
    return f"/api/users/{user_id}/"


@pytest.mark.django_db
class TestUserList:
    def test_admin_can_list(self, admin_client):
        UserFactory.create_batch(3)
        response = admin_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        # admin_user + 3 created
        assert len(response.data) >= 3

    def test_operator_can_list(self, operator_client):
        response = operator_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_readonly_cannot_list(self, readonly_client):
        response = readonly_client.get(LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_list(self, api_client):
        response = api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserCreate:
    def test_admin_can_create(self, admin_client):
        data = {
            "email": "new@example.com",
            "password": "strongpass123",
            "first_name": "New",
        }
        response = admin_client.post(LIST_URL, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="new@example.com").exists()

    def test_operator_cannot_create(self, operator_client):
        data = {"email": "new@example.com", "password": "strongpass123"}
        response = operator_client.post(LIST_URL, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_readonly_cannot_create(self, readonly_client):
        data = {"email": "new@example.com", "password": "strongpass123"}
        response = readonly_client.post(LIST_URL, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserDetail:
    def test_admin_can_retrieve(self, admin_client, operator_user):
        response = admin_client.get(detail_url(operator_user.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == operator_user.email

    def test_operator_can_retrieve(self, operator_client, admin_user):
        response = operator_client.get(detail_url(admin_user.id))
        assert response.status_code == status.HTTP_200_OK

    def test_readonly_cannot_retrieve(self, readonly_client, admin_user):
        response = readonly_client.get(detail_url(admin_user.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserUpdate:
    def test_admin_can_update(self, admin_client, operator_user):
        response = admin_client.patch(
            detail_url(operator_user.id),
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        operator_user.refresh_from_db()
        assert operator_user.first_name == "Updated"

    def test_operator_can_update(self, operator_client):
        user = UserFactory()
        response = operator_client.patch(
            detail_url(user.id), {"first_name": "Updated"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_readonly_cannot_update(self, readonly_client, admin_user):
        response = readonly_client.patch(
            detail_url(admin_user.id), {"first_name": "Hacked"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserDelete:
    def test_admin_can_delete(self, admin_client):
        user = UserFactory()
        response = admin_client.delete(detail_url(user.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=user.id).exists()

    def test_operator_cannot_delete(self, operator_client):
        user = UserFactory()
        response = operator_client.delete(detail_url(user.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_readonly_cannot_delete(self, readonly_client):
        user = UserFactory()
        response = readonly_client.delete(detail_url(user.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestMeEndpoint:
    def test_admin_can_get_me(self, admin_client, admin_user):
        response = admin_client.get(ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == admin_user.email

    def test_operator_can_get_me(self, operator_client, operator_user):
        response = operator_client.get(ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == operator_user.email

    def test_readonly_can_get_me(self, readonly_client, readonly_user):
        response = readonly_client.get(ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == readonly_user.email

    def test_admin_can_patch_me(self, admin_client):
        response = admin_client.patch(ME_URL, {"first_name": "Admin"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Admin"

    def test_operator_can_patch_me(self, operator_client):
        response = operator_client.patch(ME_URL, {"first_name": "Op"}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_readonly_cannot_patch_me(self, readonly_client):
        response = readonly_client.patch(ME_URL, {"first_name": "Hacked"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestChangePassword:
    def test_any_user_can_change_password(self, readonly_client, readonly_user):
        data = {"old_password": "testpass123", "new_password": "newpass12345"}
        response = readonly_client.post(CHANGE_PASSWORD_URL, data)
        assert response.status_code == status.HTTP_200_OK
        readonly_user.refresh_from_db()
        assert readonly_user.check_password("newpass12345")

    def test_wrong_old_password_rejected(self, admin_client):
        data = {"old_password": "wrongpass", "new_password": "newpass12345"}
        response = admin_client.post(CHANGE_PASSWORD_URL, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
