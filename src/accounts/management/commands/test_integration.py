import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from rest_framework.test import APIClient

User = get_user_model()


class Command(BaseCommand):
    help = "Run integration tests against the live Docker Compose stack"

    def handle(self, *args, **options):
        self.client = APIClient()
        self.passed = 0
        self.failed = 0

        self._setup()

        # Auth tests
        self._test_jwt_login()
        self._test_jwt_refresh()
        self._test_jwt_invalid_credentials()

        # User CRUD tests
        self._test_admin_list_users()
        self._test_admin_create_user()
        self._test_admin_retrieve_user()
        self._test_admin_update_user()
        self._test_admin_delete_user()
        self._test_operator_cannot_create_user()
        self._test_operator_cannot_delete_user()
        self._test_readonly_cannot_list_users()

        # Me endpoint tests
        self._test_me_get()
        self._test_me_patch_admin()
        self._test_me_patch_readonly_forbidden()
        self._test_change_password()

        # Group tests
        self._test_admin_list_groups()
        self._test_readonly_sees_own_groups()
        self._test_admin_create_group()
        self._test_operator_cannot_create_group()
        self._test_operator_can_update_group()
        self._test_admin_delete_group()

        # Health test
        self._test_health_endpoint()

        self.stdout.write("")
        self.stdout.write(f"Results: {self.passed} passed, {self.failed} failed")
        if self.failed > 0:
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS("All integration tests passed!"))

    def _setup(self):
        """Create test users and ensure groups exist."""
        for name in ["Admin", "Operator", "ReadOnly"]:
            Group.objects.get_or_create(name=name)

        admin_group = Group.objects.get(name="Admin")
        operator_group = Group.objects.get(name="Operator")
        readonly_group = Group.objects.get(name="ReadOnly")

        # Clean up any previous test users
        User.objects.filter(email__endswith="@integration.test").delete()

        self.admin_user = User.objects.create_user(
            email="admin@integration.test", password="adminpass123"
        )
        self.admin_user.groups.add(admin_group)

        self.operator_user = User.objects.create_user(
            email="operator@integration.test", password="operatorpass123"
        )
        self.operator_user.groups.add(operator_group)

        self.readonly_user = User.objects.create_user(
            email="readonly@integration.test", password="readonlypass123"
        )
        self.readonly_user.groups.add(readonly_group)

    def _assert(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            self.stdout.write(self.style.SUCCESS(f"  PASS: {name}"))
        else:
            self.failed += 1
            self.stdout.write(self.style.ERROR(f"  FAIL: {name} — {detail}"))

    def _login(self, email, password):
        resp = self.client.post("/api/auth/token/", {"email": email, "password": password})
        if resp.status_code == 200:
            token = resp.data["access"]
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            return resp.data
        return None

    def _login_admin(self):
        self._login("admin@integration.test", "adminpass123")

    def _login_operator(self):
        self._login("operator@integration.test", "operatorpass123")

    def _login_readonly(self):
        self._login("readonly@integration.test", "readonlypass123")

    # ── Auth ───────────────────────────────────────────────
    def _test_jwt_login(self):
        self.client.credentials()
        resp = self.client.post(
            "/api/auth/token/",
            {"email": "admin@integration.test", "password": "adminpass123"},
        )
        self._assert("JWT login returns 200", resp.status_code == 200, f"got {resp.status_code}")
        self._assert("JWT login returns access token", "access" in resp.data)
        self._assert("JWT login returns refresh token", "refresh" in resp.data)

    def _test_jwt_refresh(self):
        self.client.credentials()
        login = self.client.post(
            "/api/auth/token/",
            {"email": "admin@integration.test", "password": "adminpass123"},
        )
        resp = self.client.post("/api/auth/token/refresh/", {"refresh": login.data["refresh"]})
        self._assert("JWT refresh returns 200", resp.status_code == 200, f"got {resp.status_code}")
        self._assert("JWT refresh returns new access token", "access" in resp.data)

    def _test_jwt_invalid_credentials(self):
        self.client.credentials()
        resp = self.client.post(
            "/api/auth/token/",
            {"email": "admin@integration.test", "password": "wrong"},
        )
        self._assert("Invalid credentials returns 401", resp.status_code == 401)

    # ── User CRUD ──────────────────────────────────────────
    def _test_admin_list_users(self):
        self._login_admin()
        resp = self.client.get("/api/users/")
        self._assert("Admin can list users", resp.status_code == 200, f"got {resp.status_code}")

    def _test_admin_create_user(self):
        self._login_admin()
        resp = self.client.post(
            "/api/users/",
            {"email": "created@integration.test", "password": "newpass12345"},
            format="json",
        )
        self._assert("Admin can create user", resp.status_code == 201, f"got {resp.status_code}")

    def _test_admin_retrieve_user(self):
        self._login_admin()
        resp = self.client.get(f"/api/users/{self.operator_user.id}/")
        self._assert("Admin can retrieve user", resp.status_code == 200, f"got {resp.status_code}")

    def _test_admin_update_user(self):
        self._login_admin()
        resp = self.client.patch(
            f"/api/users/{self.operator_user.id}/",
            {"first_name": "IntegrationUpdated"},
            format="json",
        )
        self._assert("Admin can update user", resp.status_code == 200, f"got {resp.status_code}")

    def _test_admin_delete_user(self):
        self._login_admin()
        target = User.objects.create_user(email="deleteme@integration.test", password="pass12345")
        resp = self.client.delete(f"/api/users/{target.id}/")
        self._assert("Admin can delete user", resp.status_code == 204, f"got {resp.status_code}")

    def _test_operator_cannot_create_user(self):
        self._login_operator()
        resp = self.client.post(
            "/api/users/",
            {"email": "nope@integration.test", "password": "newpass12345"},
            format="json",
        )
        self._assert(
            "Operator cannot create user", resp.status_code == 403, f"got {resp.status_code}"
        )

    def _test_operator_cannot_delete_user(self):
        self._login_operator()
        resp = self.client.delete(f"/api/users/{self.readonly_user.id}/")
        self._assert(
            "Operator cannot delete user", resp.status_code == 403, f"got {resp.status_code}"
        )

    def _test_readonly_cannot_list_users(self):
        self._login_readonly()
        resp = self.client.get("/api/users/")
        self._assert(
            "ReadOnly cannot list users", resp.status_code == 403, f"got {resp.status_code}"
        )

    # ── Me ─────────────────────────────────────────────────
    def _test_me_get(self):
        self._login_admin()
        resp = self.client.get("/api/users/me/")
        self._assert("GET /me/ returns 200", resp.status_code == 200, f"got {resp.status_code}")
        self._assert(
            "GET /me/ returns correct email",
            resp.data["email"] == "admin@integration.test",
        )

    def _test_me_patch_admin(self):
        self._login_admin()
        resp = self.client.patch("/api/users/me/", {"first_name": "IntAdmin"}, format="json")
        self._assert("Admin can PATCH /me/", resp.status_code == 200, f"got {resp.status_code}")

    def _test_me_patch_readonly_forbidden(self):
        self._login_readonly()
        resp = self.client.patch("/api/users/me/", {"first_name": "Hacked"}, format="json")
        self._assert(
            "ReadOnly cannot PATCH /me/ profile fields",
            resp.status_code == 403,
            f"got {resp.status_code}",
        )

    def _test_change_password(self):
        self._login_readonly()
        resp = self.client.post(
            "/api/users/change-password/",
            {"old_password": "readonlypass123", "new_password": "newreadonly123"},
        )
        self._assert(
            "ReadOnly can change password", resp.status_code == 200, f"got {resp.status_code}"
        )
        # Reset password back
        self.readonly_user.set_password("readonlypass123")
        self.readonly_user.save()

    # ── Groups ─────────────────────────────────────────────
    def _test_admin_list_groups(self):
        self._login_admin()
        resp = self.client.get("/api/groups/")
        self._assert(
            "Admin can list all groups", resp.status_code == 200, f"got {resp.status_code}"
        )
        names = {g["name"] for g in resp.data}
        self._assert("Admin sees all 3 groups", {"Admin", "Operator", "ReadOnly"} <= names)

    def _test_readonly_sees_own_groups(self):
        self._login_readonly()
        resp = self.client.get("/api/groups/")
        self._assert(
            "ReadOnly can list groups", resp.status_code == 200, f"got {resp.status_code}"
        )
        names = {g["name"] for g in resp.data}
        self._assert("ReadOnly sees only own group", names == {"ReadOnly"}, f"got {names}")

    def _test_admin_create_group(self):
        self._login_admin()
        resp = self.client.post("/api/groups/", {"name": "IntegrationGroup"})
        self._assert("Admin can create group", resp.status_code == 201, f"got {resp.status_code}")

    def _test_operator_cannot_create_group(self):
        self._login_operator()
        resp = self.client.post("/api/groups/", {"name": "NopGroup"})
        self._assert(
            "Operator cannot create group", resp.status_code == 403, f"got {resp.status_code}"
        )

    def _test_operator_can_update_group(self):
        self._login_operator()
        group = Group.objects.get(name="IntegrationGroup")
        resp = self.client.patch(
            f"/api/groups/{group.id}/", {"name": "IntegrationRenamed"}, format="json"
        )
        self._assert(
            "Operator can update group", resp.status_code == 200, f"got {resp.status_code}"
        )

    def _test_admin_delete_group(self):
        self._login_admin()
        group = Group.objects.filter(name="IntegrationRenamed").first()
        if not group:
            group = Group.objects.create(name="ToDelete")
        resp = self.client.delete(f"/api/groups/{group.id}/")
        self._assert("Admin can delete group", resp.status_code == 204, f"got {resp.status_code}")

    # ── Health ─────────────────────────────────────────────
    def _test_health_endpoint(self):
        self.client.credentials()  # No auth
        resp = self.client.get("/api/health/")
        self._assert(
            "Health endpoint returns 200", resp.status_code == 200, f"got {resp.status_code}"
        )
        self._assert("Health status is healthy", resp.data["status"] == "healthy")
        self._assert("Health has database section", "database" in resp.data)
        self._assert(
            "Database default is up",
            resp.data.get("database", {}).get("default", {}).get("status") == "up",
            f"got {resp.data.get('database')}",
        )
        self._assert(
            "Database has latency_ms",
            "latency_ms" in resp.data.get("database", {}).get("default", {}),
        )
        self._assert("Health has migrations section", "migrations" in resp.data)
        self._assert(
            "Migrations are complete",
            resp.data.get("migrations", {}).get("status") == "complete",
            f"got {resp.data.get('migrations')}",
        )
        self._assert("Health has app section", "app" in resp.data)
        self._assert(
            "App status is healthy or warnings",
            resp.data.get("app", {}).get("status") in ("healthy", "warnings"),
            f"got {resp.data.get('app')}",
        )
