import factory
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "testpass123")
        user = model_class(*args, **kwargs)
        user.set_password(password)
        user.save()
        return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_group(db):
    return Group.objects.get_or_create(name="Admin")[0]


@pytest.fixture
def operator_group(db):
    return Group.objects.get_or_create(name="Operator")[0]


@pytest.fixture
def readonly_group(db):
    return Group.objects.get_or_create(name="ReadOnly")[0]


@pytest.fixture
def admin_user(db, admin_group):
    user = UserFactory(email="admin@example.com")
    user.groups.add(admin_group)
    return user


@pytest.fixture
def operator_user(db, operator_group):
    user = UserFactory(email="operator@example.com")
    user.groups.add(operator_group)
    return user


@pytest.fixture
def readonly_user(db, readonly_group):
    user = UserFactory(email="readonly@example.com")
    user.groups.add(readonly_group)
    return user


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def operator_client(api_client, operator_user):
    api_client.force_authenticate(user=operator_user)
    return api_client


@pytest.fixture
def readonly_client(api_client, readonly_user):
    api_client.force_authenticate(user=readonly_user)
    return api_client
