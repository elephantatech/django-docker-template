# Changelog

## [Unreleased]

### Added

- **CRUD tutorial** (`TUTORIAL.md`) — step-by-step guide to building a new API app (Products & Stock example) with models, serializers, permissions, views, URLs, admin, and tests
- **GitHub issue templates** — form-based templates for bug reports and feature requests (`.github/ISSUE_TEMPLATE/`)
- Tutorial link in README

## [2.0.0] - 2026-03-01

Complete rebuild of the Django Docker template from scratch.

### Breaking Changes

- Python upgraded from 3.8 to **3.14**
- Django upgraded from 3.1 to **6.0.2**
- `requirements.txt` replaced with **`pyproject.toml` + `uv.lock`** (uv)
- `docker-compose.yml` moved from `src/` to **project root**
- `Dockerfile` renamed from `dockerfile` to `Dockerfile` (multi-stage build with uv)
- Authentication switched from Session/Basic to **JWT (SimpleJWT)**
- `CustomUser` now uses **email as `USERNAME_FIELD`** (no username column)
- `.env_example` renamed to `.env.example`

### Added

- **JWT authentication** via `djangorestframework-simplejwt`
  - `POST /api/auth/token/` — obtain access + refresh tokens
  - `POST /api/auth/token/refresh/` — refresh access token
  - Configurable token lifetimes via environment variables
- **Group-based permission system** with three roles: Admin, Operator, ReadOnly
  - `IsAdmin`, `IsAdminOrOperator`, `IsAdminOrReadOnly` permission classes
  - `setup_groups` management command to create default groups
- **User API** (`UserViewSet` with DRF router)
  - Full CRUD at `/api/users/` with role-based access control
  - `GET /api/users/me/` — current user profile
  - `PATCH /api/users/me/` — update own profile (restricted for ReadOnly)
  - `POST /api/users/change-password/` — password change for any authenticated user
- **Group API** (`GroupViewSet` with DRF router)
  - Full CRUD at `/api/groups/` with role-based access control
  - ReadOnly users see only their own groups
- **Health endpoint** at `/api/health/` (no auth required)
  - Database connectivity check with latency measurement
  - Migration status check (complete / pending / error)
  - Cache backend check (when configured)
  - Application health check (installed apps, URL config, settings warnings)
  - Overall status: `healthy`, `degraded`, or `unhealthy`
- **Prometheus metrics** via `django-prometheus`
  - `/metrics` endpoint
  - Prometheus container in docker-compose scraping the Django app
- **Structured JSON logging**
  - `JSONFormatter` — all logs as single-line JSON with timestamp, level, logger, message
  - `PasswordRedactionFilter` — redacts password values from log messages and extras
- **Comprehensive test suite** (105 tests)
  - `accounts/tests/test_models.py` — CustomUser and manager
  - `accounts/tests/test_serializers.py` — all serializers
  - `accounts/tests/test_views_users.py` — user endpoints and permission matrix
  - `accounts/tests/test_views_groups.py` — group endpoints and permission matrix
  - `accounts/tests/test_permissions.py` — permission class unit tests
  - `accounts/tests/test_auth.py` — JWT login, refresh, token validation
  - `health/tests/test_health.py` — health endpoint and individual check functions
  - `logging_utils/tests/test_logging.py` — JSON formatter and password filter
- **Integration test suite** (`manage.py test_integration`)
  - Runs against live Docker Compose stack
  - Tests full JWT auth flow, permission matrix, CRUD, health endpoint
- **CI/CD** via GitHub Actions (`.github/workflows/ci.yml`)
  - Lint job (ruff check + format)
  - Test job (pytest with PostgreSQL 17 service)
  - Integration job (full docker-compose stack)
- **Multi-stage Dockerfile** with uv, non-root user, gunicorn
- **`pyproject.toml`** with ruff and pytest configuration
- **`CONTRIBUTING.md`** with development workflow, code standards, and PR rules
- **`README.md`** with getting started guide, API reference, and test instructions

### Changed

- Database driver switched from `psycopg2-binary` to **`psycopg[binary]` v3**
- PostgreSQL upgraded from unversioned to **PostgreSQL 17**
- Settings now fully env-driven via **`environs[django]`** (DATABASE_URL, SECRET_KEY, etc.)
- Linting/formatting handled by **ruff** (replaces no prior tooling)
- Testing handled by **pytest + pytest-django + factory-boy** (replaces empty test file)

### Removed

- `requirements.txt` (replaced by `pyproject.toml` + `uv.lock`)
- `changelog.md` (replaced by `CHANGELOG.md`)
- `readme.md` (replaced by `README.md`)
- `.env_example` (replaced by `.env.example`)
- `.gitattributes`
- Session and Basic authentication
- `python-dotenv` dependency (replaced by `environs`)

## [1.0.0] - 2021-02-01

### Added

- Initial Django 3.0 project with Docker and PostgreSQL
- Custom user model (empty placeholder)
- Basic DRF user list and detail views
- Docker Compose with PostgreSQL and Django services
