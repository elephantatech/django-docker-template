import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIRequestFactory

from accounts.serializers import (
    MeSerializer,
    PasswordChangeSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)
from conftest import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserListSerializer:
    def test_fields(self):
        user = UserFactory()
        serializer = UserListSerializer(user)
        assert set(serializer.data.keys()) == {
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "groups",
        }

    def test_read_only(self):
        serializer = UserListSerializer()
        for field_name in serializer.fields:
            assert serializer.fields[field_name].read_only


@pytest.mark.django_db
class TestUserCreateSerializer:
    def test_valid_data(self):
        data = {
            "email": "new@example.com",
            "password": "strongpass123",
            "first_name": "Jane",
            "last_name": "Doe",
        }
        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.check_password("strongpass123")

    def test_short_password_rejected(self):
        data = {"email": "new@example.com", "password": "short"}
        serializer = UserCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "password" in serializer.errors

    def test_create_with_groups(self):
        group = Group.objects.create(name="TestGroup")
        data = {
            "email": "new@example.com",
            "password": "strongpass123",
            "group_ids": [group.pk],
        }
        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert group in user.groups.all()


@pytest.mark.django_db
class TestUserUpdateSerializer:
    def test_update_fields(self):
        user = UserFactory()
        serializer = UserUpdateSerializer(user, data={"first_name": "Updated"}, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.first_name == "Updated"

    def test_update_groups(self):
        user = UserFactory()
        group = Group.objects.create(name="NewGroup")
        serializer = UserUpdateSerializer(user, data={"group_ids": [group.pk]}, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert group in updated.groups.all()


@pytest.mark.django_db
class TestPasswordChangeSerializer:
    def test_valid_change(self):
        user = UserFactory(password="oldpassword1")
        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = user
        data = {"old_password": "oldpassword1", "new_password": "newpassword1"}
        serializer = PasswordChangeSerializer(data=data, context={"request": request})
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        user.refresh_from_db()
        assert user.check_password("newpassword1")

    def test_wrong_old_password(self):
        user = UserFactory(password="oldpassword1")
        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = user
        data = {"old_password": "wrongpassword", "new_password": "newpassword1"}
        serializer = PasswordChangeSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "old_password" in serializer.errors


@pytest.mark.django_db
class TestMeSerializer:
    def test_fields(self):
        user = UserFactory()
        serializer = MeSerializer(user)
        assert "email" in serializer.data
        assert "groups" in serializer.data

    def test_read_only_fields(self):
        serializer = MeSerializer()
        assert serializer.fields["id"].read_only
        assert serializer.fields["date_joined"].read_only
        assert serializer.fields["is_active"].read_only
