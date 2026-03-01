import pytest
from django.contrib.auth.models import Group
from rest_framework import status

GROUPS_URL = "/api/groups/"


def detail_url(group_id):
    return f"/api/groups/{group_id}/"


@pytest.mark.django_db
class TestGroupList:
    def test_admin_sees_all_groups(
        self, admin_client, admin_group, operator_group, readonly_group
    ):
        response = admin_client.get(GROUPS_URL)
        assert response.status_code == status.HTTP_200_OK
        names = {g["name"] for g in response.data}
        assert {"Admin", "Operator", "ReadOnly"} <= names

    def test_operator_sees_all_groups(
        self, operator_client, admin_group, operator_group, readonly_group
    ):
        response = operator_client.get(GROUPS_URL)
        assert response.status_code == status.HTTP_200_OK
        names = {g["name"] for g in response.data}
        assert {"Admin", "Operator", "ReadOnly"} <= names

    def test_readonly_sees_own_groups_only(self, readonly_client, admin_group, readonly_group):
        response = readonly_client.get(GROUPS_URL)
        assert response.status_code == status.HTTP_200_OK
        names = {g["name"] for g in response.data}
        assert names == {"ReadOnly"}

    def test_unauthenticated_cannot_list(self, api_client):
        response = api_client.get(GROUPS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGroupCreate:
    def test_admin_can_create(self, admin_client):
        response = admin_client.post(GROUPS_URL, {"name": "NewGroup"})
        assert response.status_code == status.HTTP_201_CREATED
        assert Group.objects.filter(name="NewGroup").exists()

    def test_operator_cannot_create(self, operator_client):
        response = operator_client.post(GROUPS_URL, {"name": "NewGroup"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_readonly_cannot_create(self, readonly_client):
        response = readonly_client.post(GROUPS_URL, {"name": "NewGroup"})
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestGroupUpdate:
    def test_admin_can_update(self, admin_client, operator_group):
        response = admin_client.patch(
            detail_url(operator_group.id), {"name": "Renamed"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        operator_group.refresh_from_db()
        assert operator_group.name == "Renamed"

    def test_operator_can_update(self, operator_client, readonly_group):
        response = operator_client.patch(
            detail_url(readonly_group.id), {"name": "Renamed"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_readonly_cannot_update(self, readonly_client, admin_group):
        response = readonly_client.patch(
            detail_url(admin_group.id), {"name": "Hacked"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestGroupDelete:
    def test_admin_can_delete(self, admin_client):
        group = Group.objects.create(name="Deletable")
        response = admin_client.delete(detail_url(group.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Group.objects.filter(id=group.id).exists()

    def test_operator_cannot_delete(self, operator_client, readonly_group):
        response = operator_client.delete(detail_url(readonly_group.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_readonly_cannot_delete(self, readonly_client, operator_group):
        response = readonly_client.delete(detail_url(operator_group.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN
