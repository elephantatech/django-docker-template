# Testing Plan

This document covers how to run tests, what each test suite covers, and manual testing procedures for QA.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Running Tests](#running-tests)
  - [Unit Tests (Local)](#unit-tests-local)
  - [Unit Tests (Docker Compose)](#unit-tests-docker-compose)
  - [Integration Tests (Docker Compose)](#integration-tests-docker-compose)
- [Manual Testing](#manual-testing)
  - [Environment Setup](#environment-setup)
  - [Authentication Flow](#authentication-flow)
  - [User Management](#user-management)
  - [Group Management](#group-management)
  - [Health Endpoint](#health-endpoint)
  - [Prometheus Metrics](#prometheus-metrics)
- [Permission Matrix Reference](#permission-matrix-reference)
- [Test Inventory](#test-inventory)
  - [Unit Tests (105 tests)](#unit-tests-105-tests)
  - [Integration Tests (36 assertions)](#integration-tests-36-assertions)

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for local development
- [Docker](https://docs.docker.com/get-docker/) and `docker-compose` for containerized testing
- A terminal with `curl` for manual testing

## Running Tests

### Unit Tests (Local)

Unit tests use SQLite and run without Docker.

```bash
cd src
uv sync --all-extras
uv run pytest -v
```

To run a specific test file or class:

```bash
# Single file
uv run pytest accounts/tests/test_auth.py -v

# Single class
uv run pytest accounts/tests/test_views_users.py::TestUserCreate -v

# Single test
uv run pytest accounts/tests/test_models.py::TestCustomUser::test_create_user -v
```

To run with coverage (if installed):

```bash
uv run pytest --cov=. --cov-report=term-missing -v
```

### Unit Tests (Docker Compose)

Run unit tests against a real PostgreSQL database inside Docker.

```bash
# Start the database
docker-compose up -d db

# Run tests inside the web container
docker-compose run --rm web /app/.venv/bin/pytest -v

# Shut down
docker-compose down
```

### Integration Tests (Docker Compose)

Integration tests run against the full live stack and test real HTTP flows, JWT authentication, and the complete permission matrix.

**Option 1: Use the integration script**

```bash
./scripts/run-integration-tests.sh
```

This handles everything automatically: builds services, waits for readiness, runs migrations, sets up groups, runs tests, verifies health/metrics, and cleans up on exit.

**Option 2: Step by step**

```bash
# 1. Build and start all services
docker-compose up -d --build

# 2. Wait for the web service to be ready
#    Check until this returns a JSON response:
curl http://localhost:8000/api/health/

# 3. Run migrations
docker-compose exec web /app/.venv/bin/python manage.py migrate

# 4. Create permission groups
docker-compose exec web /app/.venv/bin/python manage.py setup_groups

# 5. Run integration tests
docker-compose exec web /app/.venv/bin/python manage.py test_integration

# 6. Shut down when done
docker-compose down -v
```

**Expected output:**

```
  PASS: JWT login returns 200
  PASS: JWT login returns access token
  PASS: JWT login returns refresh token
  ...
  PASS: App status is healthy or warnings

Results: 36 passed, 0 failed
All integration tests passed!
```

### Linting

Run before submitting any code:

```bash
cd src
uv run ruff check .
uv run ruff format --check .
```

---

## Manual Testing

Use these steps to manually verify the application end-to-end. All examples assume the stack is running on `localhost:8000`.

### Environment Setup

```bash
# Start the stack
docker-compose up -d --build

# Wait for readiness
curl http://localhost:8000/api/health/

# Run migrations and create groups
docker-compose exec web /app/.venv/bin/python manage.py migrate
docker-compose exec web /app/.venv/bin/python manage.py setup_groups

# Create a superuser for admin access
docker-compose exec web /app/.venv/bin/python manage.py createsuperuser
# Enter: email, password when prompted
```

### Authentication Flow

**1. Obtain a JWT token**

```bash
curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}' | python3 -m json.tool
```

Expected: HTTP 200 with `access` and `refresh` tokens.

**2. Use the access token**

```bash
export TOKEN="<access token from step 1>"

curl -s http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: HTTP 200 with the current user's profile.

**3. Refresh an expired token**

```bash
curl -s -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh token from step 1>"}' | python3 -m json.tool
```

Expected: HTTP 200 with a new `access` token.

**4. Verify invalid credentials are rejected**

```bash
curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "wrongpassword"}'
```

Expected: HTTP 401.

**5. Verify expired/invalid tokens are rejected**

```bash
curl -s http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer invalid-token-here"
```

Expected: HTTP 401.

### User Management

Set `$TOKEN` to a valid Admin user token for these tests.

**List users (Admin)**

```bash
curl -s http://localhost:8000/api/users/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: HTTP 200 with list of all users.

**Create a user (Admin)**

```bash
curl -s -X POST http://localhost:8000/api/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "password": "securepass123", "first_name": "New", "last_name": "User"}' | python3 -m json.tool
```

Expected: HTTP 201 with user data (no password in response).

**Update a user (Admin)**

```bash
curl -s -X PATCH http://localhost:8000/api/users/2/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Updated"}' | python3 -m json.tool
```

Expected: HTTP 200.

**Delete a user (Admin)**

```bash
curl -s -X DELETE http://localhost:8000/api/users/2/ \
  -H "Authorization: Bearer $TOKEN"
```

Expected: HTTP 204 (no body).

**Get own profile**

```bash
curl -s http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: HTTP 200 with email, first_name, last_name, groups.

**Change password**

```bash
curl -s -X POST http://localhost:8000/api/users/change-password/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"old_password": "currentpass", "new_password": "newpass12345"}'
```

Expected: HTTP 200 with `{"detail": "Password updated."}`.

### Group Management

**List groups**

```bash
curl -s http://localhost:8000/api/groups/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: HTTP 200. Admin/Operator see all groups; ReadOnly sees only own groups.

**Create a group (Admin only)**

```bash
curl -s -X POST http://localhost:8000/api/groups/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "NewGroup"}'
```

Expected: HTTP 201.

**Delete a group (Admin only)**

```bash
curl -s -X DELETE http://localhost:8000/api/groups/4/ \
  -H "Authorization: Bearer $TOKEN"
```

Expected: HTTP 204.

### Health Endpoint

No authentication required.

```bash
curl -s http://localhost:8000/api/health/ | python3 -m json.tool
```

Expected response:

```json
{
    "status": "healthy",
    "database": {
        "default": {
            "status": "up",
            "latency_ms": 1.23
        }
    },
    "migrations": {
        "status": "complete"
    },
    "app": {
        "status": "healthy"
    }
}
```

Verify:
- `status` is `healthy`, `degraded`, or `unhealthy`
- `database.default.status` is `up` with a numeric `latency_ms`
- `migrations.status` is `complete` (no pending migrations)
- `app.status` is `healthy` or `warnings`
- If a cache backend is configured, `cache` section is present

### Prometheus Metrics

**Django metrics endpoint (no auth)**

```bash
curl -s http://localhost:8000/metrics | head -20
```

Expected: Prometheus text format with `django_` prefixed metrics.

**Prometheus UI**

Open http://localhost:9090 in a browser. Verify the `django` target appears under Status > Targets.

---

## Permission Matrix Reference

Use this table when testing access control. Each cell shows the expected HTTP status code.

### User Endpoints

| Endpoint | Method | Admin | Operator | ReadOnly | No Auth |
|---|---|---|---|---|---|
| `/api/users/` | GET | 200 | 200 | 403 | 401 |
| `/api/users/` | POST | 201 | 403 | 403 | 401 |
| `/api/users/{id}/` | GET | 200 | 200 | 403 | 401 |
| `/api/users/{id}/` | PATCH | 200 | 200 | 403 | 401 |
| `/api/users/{id}/` | DELETE | 204 | 403 | 403 | 401 |
| `/api/users/me/` | GET | 200 | 200 | 200 | 401 |
| `/api/users/me/` | PATCH | 200 | 200 | 403 | 401 |
| `/api/users/change-password/` | POST | 200 | 200 | 200 | 401 |

### Group Endpoints

| Endpoint | Method | Admin | Operator | ReadOnly | No Auth |
|---|---|---|---|---|---|
| `/api/groups/` | GET | 200 (all) | 200 (all) | 200 (own only) | 401 |
| `/api/groups/` | POST | 201 | 403 | 403 | 401 |
| `/api/groups/{id}/` | PATCH | 200 | 200 | 403 | 401 |
| `/api/groups/{id}/` | DELETE | 204 | 403 | 403 | 401 |

### Other Endpoints

| Endpoint | Method | Auth Required | Expected |
|---|---|---|---|
| `/api/health/` | GET | No | 200 |
| `/metrics` | GET | No | 200 |
| `/api/auth/token/` | POST | No | 200 (valid creds) / 401 (invalid) |
| `/api/auth/token/refresh/` | POST | No | 200 (valid refresh) / 401 (invalid) |

---

## Test Inventory

### Unit Tests (105 tests)

#### Authentication — `accounts/tests/test_auth.py` (6 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_obtain_token` | POST `/api/auth/token/` returns access + refresh tokens |
| 2 | `test_obtain_token_wrong_password` | Wrong password returns 401 |
| 3 | `test_refresh_token` | POST `/api/auth/token/refresh/` returns new access token |
| 4 | `test_access_with_token` | Bearer token grants access to protected endpoint |
| 5 | `test_invalid_token_rejected` | Invalid Bearer token returns 401 |
| 6 | `test_inactive_user_cannot_login` | Inactive user cannot obtain tokens |

#### User Model — `accounts/tests/test_models.py` (9 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_create_user` | User created with email, is_active=True, is_staff=False |
| 2 | `test_create_user_no_email_raises` | Empty email raises ValueError |
| 3 | `test_create_superuser` | Superuser has is_staff=True, is_superuser=True |
| 4 | `test_create_superuser_not_staff_raises` | is_staff=False raises ValueError |
| 5 | `test_create_superuser_not_superuser_raises` | is_superuser=False raises ValueError |
| 6 | `test_email_is_username_field` | USERNAME_FIELD is "email" |
| 7 | `test_str_returns_email` | str(user) returns email |
| 8 | `test_email_normalized` | Domain part of email is lowercased |
| 9 | `test_user_with_names` | first_name and last_name are saved |

#### Permissions — `accounts/tests/test_permissions.py` (13 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `IsAdmin: test_admin_allowed` | Admin group passes IsAdmin |
| 2 | `IsAdmin: test_operator_denied` | Operator group fails IsAdmin |
| 3 | `IsAdmin: test_readonly_denied` | ReadOnly group fails IsAdmin |
| 4 | `IsAdmin: test_no_group_denied` | User with no group fails IsAdmin |
| 5 | `IsAdminOrOperator: test_admin_allowed` | Admin passes IsAdminOrOperator |
| 6 | `IsAdminOrOperator: test_operator_allowed` | Operator passes IsAdminOrOperator |
| 7 | `IsAdminOrOperator: test_readonly_denied` | ReadOnly fails IsAdminOrOperator |
| 8 | `IsAdminOrReadOnly: test_admin_get` | Admin GET passes |
| 9 | `IsAdminOrReadOnly: test_admin_post` | Admin POST passes |
| 10 | `IsAdminOrReadOnly: test_operator_get` | Operator GET passes |
| 11 | `IsAdminOrReadOnly: test_operator_post` | Operator POST denied |
| 12 | `IsAdminOrReadOnly: test_readonly_get` | ReadOnly GET denied |
| 13 | `IsAdminOrReadOnly: test_readonly_post` | ReadOnly POST denied |

#### Serializers — `accounts/tests/test_serializers.py` (11 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `UserListSerializer: test_fields` | Correct fields returned |
| 2 | `UserListSerializer: test_read_only` | All fields are read-only |
| 3 | `UserCreateSerializer: test_valid_data` | User created with hashed password |
| 4 | `UserCreateSerializer: test_short_password_rejected` | Password < 8 chars rejected |
| 5 | `UserCreateSerializer: test_create_with_groups` | Group assignment via group_ids |
| 6 | `UserUpdateSerializer: test_update_fields` | Partial update works |
| 7 | `UserUpdateSerializer: test_update_groups` | Group reassignment works |
| 8 | `PasswordChangeSerializer: test_valid_change` | Password changed successfully |
| 9 | `PasswordChangeSerializer: test_wrong_old_password` | Wrong old password rejected |
| 10 | `MeSerializer: test_fields` | Correct fields returned |
| 11 | `MeSerializer: test_read_only_fields` | id, date_joined, is_active are read-only |

#### User Views — `accounts/tests/test_views_users.py` (20 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_admin_can_list` | Admin GET `/api/users/` returns 200 |
| 2 | `test_operator_can_list` | Operator GET `/api/users/` returns 200 |
| 3 | `test_readonly_cannot_list` | ReadOnly GET `/api/users/` returns 403 |
| 4 | `test_unauthenticated_cannot_list` | No auth GET `/api/users/` returns 401 |
| 5 | `test_admin_can_create` | Admin POST `/api/users/` returns 201 |
| 6 | `test_operator_cannot_create` | Operator POST `/api/users/` returns 403 |
| 7 | `test_readonly_cannot_create` | ReadOnly POST `/api/users/` returns 403 |
| 8 | `test_admin_can_retrieve` | Admin GET `/api/users/{id}/` returns 200 |
| 9 | `test_operator_can_retrieve` | Operator GET `/api/users/{id}/` returns 200 |
| 10 | `test_readonly_cannot_retrieve` | ReadOnly GET `/api/users/{id}/` returns 403 |
| 11 | `test_admin_can_update` | Admin PATCH `/api/users/{id}/` returns 200 |
| 12 | `test_operator_can_update` | Operator PATCH returns 200 |
| 13 | `test_readonly_cannot_update` | ReadOnly PATCH returns 403 |
| 14 | `test_admin_can_delete` | Admin DELETE returns 204, user removed |
| 15 | `test_operator_cannot_delete` | Operator DELETE returns 403 |
| 16 | `test_readonly_cannot_delete` | ReadOnly DELETE returns 403 |
| 17 | `test_admin_can_get_me` | Admin GET `/api/users/me/` returns own profile |
| 18 | `test_operator_can_get_me` | Operator GET `/api/users/me/` returns own profile |
| 19 | `test_readonly_can_get_me` | ReadOnly GET `/api/users/me/` returns own profile |
| 20 | `test_admin_can_patch_me` | Admin PATCH `/api/users/me/` updates profile |
| 21 | `test_operator_can_patch_me` | Operator PATCH `/api/users/me/` updates profile |
| 22 | `test_readonly_cannot_patch_me` | ReadOnly PATCH `/api/users/me/` returns 403 |
| 23 | `test_any_user_can_change_password` | ReadOnly POST `/api/users/change-password/` works |
| 24 | `test_wrong_old_password_rejected` | Wrong old password returns 400 |

#### Group Views — `accounts/tests/test_views_groups.py` (12 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_admin_sees_all_groups` | Admin sees Admin, Operator, ReadOnly groups |
| 2 | `test_operator_sees_all_groups` | Operator sees all groups |
| 3 | `test_readonly_sees_own_groups_only` | ReadOnly sees only ReadOnly group |
| 4 | `test_unauthenticated_cannot_list` | No auth returns 401 |
| 5 | `test_admin_can_create` | Admin POST `/api/groups/` returns 201 |
| 6 | `test_operator_cannot_create` | Operator POST returns 403 |
| 7 | `test_readonly_cannot_create` | ReadOnly POST returns 403 |
| 8 | `test_admin_can_update` | Admin PATCH returns 200 |
| 9 | `test_operator_can_update` | Operator PATCH returns 200 |
| 10 | `test_readonly_cannot_update` | ReadOnly PATCH returns 403 |
| 11 | `test_admin_can_delete` | Admin DELETE returns 204 |
| 12 | `test_operator_cannot_delete` | Operator DELETE returns 403 |
| 13 | `test_readonly_cannot_delete` | ReadOnly DELETE returns 403 |

#### Health — `health/tests/test_health.py` (19 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_healthy_response` | Returns 200 with status "healthy" |
| 2 | `test_no_auth_required` | No Bearer token needed |
| 3 | `test_response_contains_all_sections` | Response has database, migrations, app |
| 4 | `test_unhealthy_when_db_down` | Database failure returns 503 "unhealthy" |
| 5 | `test_degraded_when_cache_down` | Cache failure returns 200 "degraded" |
| 6 | `test_degraded_when_migrations_pending` | Pending migrations returns "degraded" |
| 7 | `test_returns_up_for_default` | Database check returns "up" with latency |
| 8 | `test_returns_down_on_failure` | Database check returns "down" on error |
| 9 | `test_latency_is_numeric` | latency_ms is a float |
| 10 | `test_complete_when_all_applied` | Migrations check returns "complete" |
| 11 | `test_pending_when_unapplied` | Unapplied migrations listed as "pending" |
| 12 | `test_error_on_exception` | Migration check error handled |
| 13 | `test_no_caches_returns_empty` | No crash when default cache configured |
| 14 | `test_locmem_cache_up` | LocMem cache returns "up" |
| 15 | `test_cache_down_on_failure` | Cache failure returns "down" |
| 16 | `test_healthy_app` | App check returns "healthy" or "warnings" |
| 17 | `test_warns_on_default_secret_key` | Default SECRET_KEY triggers warning |
| 18 | `test_warns_on_debug_enabled` | DEBUG=True triggers warning |
| 19 | `test_verifies_required_apps` | Required apps are installed |

#### Logging — `logging_utils/tests/test_logging.py` (10 tests)

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_basic_format` | JSON output has timestamp, level, logger, message |
| 2 | `test_single_line` | Output contains no newlines |
| 3 | `test_exception_included` | Exception traceback in JSON output |
| 4 | `test_extra_fields_included` | Extra kwargs appear in JSON output |
| 5 | `test_redacts_password_in_message` | `password=secret` redacted in msg |
| 6 | `test_redacts_password_in_json_message` | `"password": "secret"` redacted in msg |
| 7 | `test_redacts_password_in_dict_args` | Password key in dict args redacted |
| 8 | `test_redacts_password_extra_attr` | Password extra attribute redacted |
| 9 | `test_preserves_non_password_messages` | Non-password messages unchanged |
| 10 | `test_returns_true` | Filter returns True (does not suppress logs) |

### Integration Tests (36 assertions)

These run via `manage.py test_integration` against the live Docker Compose stack.

#### Authentication (6 assertions)

| # | Assertion | Expected |
|---|---|---|
| 1 | JWT login returns 200 | HTTP 200 |
| 2 | JWT login returns access token | `access` in response |
| 3 | JWT login returns refresh token | `refresh` in response |
| 4 | JWT refresh returns 200 | HTTP 200 |
| 5 | JWT refresh returns new access token | `access` in response |
| 6 | Invalid credentials returns 401 | HTTP 401 |

#### User CRUD (8 assertions)

| # | Assertion | Expected |
|---|---|---|
| 7 | Admin can list users | HTTP 200 |
| 8 | Admin can create user | HTTP 201 |
| 9 | Admin can retrieve user | HTTP 200 |
| 10 | Admin can update user | HTTP 200 |
| 11 | Admin can delete user | HTTP 204 |
| 12 | Operator cannot create user | HTTP 403 |
| 13 | Operator cannot delete user | HTTP 403 |
| 14 | ReadOnly cannot list users | HTTP 403 |

#### Me Endpoint (5 assertions)

| # | Assertion | Expected |
|---|---|---|
| 15 | GET /me/ returns 200 | HTTP 200 |
| 16 | GET /me/ returns correct email | Matches logged-in user |
| 17 | Admin can PATCH /me/ | HTTP 200 |
| 18 | ReadOnly cannot PATCH /me/ profile fields | HTTP 403 |
| 19 | ReadOnly can change password | HTTP 200 |

#### Groups (8 assertions)

| # | Assertion | Expected |
|---|---|---|
| 20 | Admin can list all groups | HTTP 200 |
| 21 | Admin sees all 3 groups | Admin, Operator, ReadOnly present |
| 22 | ReadOnly can list groups | HTTP 200 |
| 23 | ReadOnly sees only own group | Only ReadOnly group returned |
| 24 | Admin can create group | HTTP 201 |
| 25 | Operator cannot create group | HTTP 403 |
| 26 | Operator can update group | HTTP 200 |
| 27 | Admin can delete group | HTTP 204 |

#### Health (9 assertions)

| # | Assertion | Expected |
|---|---|---|
| 28 | Health endpoint returns 200 | HTTP 200 |
| 29 | Health status is healthy | `status` = `healthy` |
| 30 | Health has database section | `database` key present |
| 31 | Database default is up | `database.default.status` = `up` |
| 32 | Database has latency_ms | `latency_ms` key present |
| 33 | Health has migrations section | `migrations` key present |
| 34 | Migrations are complete | `migrations.status` = `complete` |
| 35 | Health has app section | `app` key present |
| 36 | App status is healthy or warnings | `app.status` in (`healthy`, `warnings`) |
