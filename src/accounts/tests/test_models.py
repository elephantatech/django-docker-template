import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCustomUser:
    def test_create_user(self):
        user = User.objects.create_user(email="test@example.com", password="pass1234")
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("pass1234")

    def test_create_user_no_email_raises(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(email="", password="pass1234")

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass1234")
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_create_superuser_not_staff_raises(self):
        with pytest.raises(ValueError, match="is_staff=True"):
            User.objects.create_superuser(
                email="admin@example.com", password="pass1234", is_staff=False
            )

    def test_create_superuser_not_superuser_raises(self):
        with pytest.raises(ValueError, match="is_superuser=True"):
            User.objects.create_superuser(
                email="admin@example.com", password="pass1234", is_superuser=False
            )

    def test_email_is_username_field(self):
        assert User.USERNAME_FIELD == "email"

    def test_str_returns_email(self):
        user = User.objects.create_user(email="test@example.com", password="pass1234")
        assert str(user) == "test@example.com"

    def test_email_normalized(self):
        user = User.objects.create_user(email="Test@EXAMPLE.com", password="pass1234")
        assert user.email == "Test@example.com"

    def test_user_with_names(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="pass1234",
            first_name="John",
            last_name="Doe",
        )
        assert user.first_name == "John"
        assert user.last_name == "Doe"
