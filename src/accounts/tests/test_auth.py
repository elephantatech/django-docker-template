import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from conftest import UserFactory

User = get_user_model()

TOKEN_URL = "/api/auth/token/"
REFRESH_URL = "/api/auth/token/refresh/"


@pytest.mark.django_db
class TestJWTAuth:
    def test_obtain_token(self, api_client):
        UserFactory(email="jwt@example.com", password="testpass123")
        response = api_client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "testpass123"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_wrong_password(self, api_client):
        UserFactory(email="jwt@example.com", password="testpass123")
        response = api_client.post(TOKEN_URL, {"email": "jwt@example.com", "password": "wrong"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client):
        UserFactory(email="jwt@example.com", password="testpass123")
        token_response = api_client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "testpass123"}
        )
        refresh = token_response.data["refresh"]
        response = api_client.post(REFRESH_URL, {"refresh": refresh})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_access_with_token(self, api_client):
        UserFactory(email="jwt@example.com", password="testpass123")
        token_response = api_client.post(
            TOKEN_URL, {"email": "jwt@example.com", "password": "testpass123"}
        )
        access = token_response.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.get("/api/users/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "jwt@example.com"

    def test_invalid_token_rejected(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        response = api_client.get("/api/users/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_cannot_login(self, api_client):
        UserFactory(email="inactive@example.com", password="testpass123", is_active=False)
        response = api_client.post(
            TOKEN_URL, {"email": "inactive@example.com", "password": "testpass123"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
