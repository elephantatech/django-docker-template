# Django Docker Template

A production-ready Django boilerplate with Docker, JWT authentication, group-based permissions, structured logging, health monitoring, and Prometheus metrics.

## Tech Stack

- **Python 3.14** / **Django 6.0**
- **Django REST Framework** with **SimpleJWT** authentication
- **PostgreSQL 17**
- **uv** for dependency management
- **ruff** for linting and formatting
- **pytest** + **factory-boy** for testing
- **Prometheus** for metrics
- **Docker** + **Docker Compose** for containerization
- **GitHub Actions** for CI

## Getting Started

### Use This Template

1. Click **"Use this template"** on GitHub to create a new repository from this template.
2. Clone your new repository:

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

3. Copy the environment file:

```bash
cp .env.example .env
```

4. Update `.env` with your own values. At minimum, change `SECRET_KEY` for production.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (for local development without Docker)

## Development

### Option 1: Docker Compose (Recommended)

Start all services (Django, PostgreSQL, Prometheus):

```bash
docker compose up --build
```

In a separate terminal, run the initial setup:

```bash
# Apply database migrations
docker compose exec web /app/.venv/bin/python manage.py migrate

# Create the default permission groups (Admin, Operator, ReadOnly)
docker compose exec web /app/.venv/bin/python manage.py setup_groups

# Create a superuser
docker compose exec web /app/.venv/bin/python manage.py createsuperuser
```

The services will be available at:

| Service | URL |
|---|---|
| Django API | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin/ |
| Health Check | http://localhost:8000/api/health/ |
| Prometheus Metrics | http://localhost:8000/metrics |
| Prometheus UI | http://localhost:9090 |

### Option 2: Local Development with uv

```bash
cd src

# Install all dependencies (including dev)
uv sync --all-extras

# Set DATABASE_URL to a local or remote Postgres instance
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/app

# Apply migrations and setup
uv run python manage.py migrate
uv run python manage.py setup_groups
uv run python manage.py createsuperuser

# Start the development server
uv run python manage.py runserver
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/token/` | Obtain JWT access + refresh tokens |
| POST | `/api/auth/token/refresh/` | Refresh an access token |

Login with email and password:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

Use the access token for authenticated requests:

```bash
curl http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer <access_token>"
```

### Users

| Method | Endpoint | Admin | Operator | ReadOnly |
|---|---|---|---|---|
| GET | `/api/users/` | All users | All users | 403 |
| POST | `/api/users/` | Create | 403 | 403 |
| GET | `/api/users/{id}/` | Any | Any | 403 |
| PUT/PATCH | `/api/users/{id}/` | Any field | Any field | 403 |
| DELETE | `/api/users/{id}/` | Allowed | 403 | 403 |
| GET | `/api/users/me/` | Own profile | Own profile | Own profile |
| PATCH | `/api/users/me/` | Any field | Any field | 403 |
| POST | `/api/users/change-password/` | Allowed | Allowed | Allowed |

### Groups

| Method | Endpoint | Admin | Operator | ReadOnly |
|---|---|---|---|---|
| GET | `/api/groups/` | All groups | All groups | Own groups only |
| POST | `/api/groups/` | Create | 403 | 403 |
| PUT/PATCH | `/api/groups/{id}/` | Allowed | Allowed | 403 |
| DELETE | `/api/groups/{id}/` | Allowed | 403 | 403 |

### Monitoring

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| GET | `/api/health/` | No | Comprehensive health check |
| GET | `/metrics` | No | Prometheus metrics |

#### Health Endpoint Response

`GET /api/health/` returns a comprehensive health report covering all services:

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

When a cache backend is configured, a `cache` section is included as well.

**Status values:**

| Overall Status | HTTP Code | Meaning |
|---|---|---|
| `healthy` | 200 | All services operational |
| `degraded` | 200 | Non-critical issue (cache down, pending migrations) |
| `unhealthy` | 503 | Critical failure (database unreachable) |

**Individual checks:**

| Check | What it verifies |
|---|---|
| `database` | Connectivity and response time for each configured database |
| `migrations` | Whether all Django migrations have been applied |
| `cache` | Cache backend read/write (only shown when cache is configured) |
| `app` | Installed apps loaded, URL config valid, settings warnings (default SECRET_KEY, DEBUG on) |

## Running Tests

### Unit Tests (Local)

```bash
cd src
uv sync --all-extras
uv run pytest -v
```

### Unit Tests (Docker)

Build the image and run pytest inside the container:

```bash
docker compose build web

docker compose run --rm \
  -e DATABASE_URL=sqlite:///test.db \
  web /app/.venv/bin/pytest -v
```

### Unit Tests (Docker Compose with PostgreSQL)

Run the tests against a real PostgreSQL database using Docker Compose:

```bash
# Start the database
docker compose up -d db

# Wait for the database to be ready, then run tests
docker compose run --rm web /app/.venv/bin/pytest -v

# Shut down when done
docker compose down
```

### Integration Tests (Docker Compose)

The integration test suite runs against the full Docker Compose stack and tests the complete JWT auth flow, permission matrix, and all CRUD operations:

```bash
# Start all services
docker compose up -d --build

# Run migrations and setup
docker compose exec web /app/.venv/bin/python manage.py migrate
docker compose exec web /app/.venv/bin/python manage.py setup_groups

# Run the integration test suite
docker compose exec web /app/.venv/bin/python manage.py test_integration

# Shut down when done
docker compose down -v
```

The integration tests cover:
- JWT login, token refresh, and invalid credential handling
- Full user CRUD with permission checks for Admin, Operator, and ReadOnly roles
- `/me/` endpoint access and restrictions
- Password change flow
- Group CRUD with permission checks
- Health endpoint availability

### Linting and Formatting

```bash
cd src

# Check for lint errors
uv run ruff check .

# Auto-fix lint errors
uv run ruff check . --fix

# Check formatting
uv run ruff format --check .

# Auto-format
uv run ruff format .
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `false` | Enable Django debug mode |
| `SECRET_KEY` | `change-me-in-production` | Django secret key |
| `ALLOWED_HOSTS` | `*` | Comma-separated list of allowed hosts |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | Database connection URL |
| `POSTGRES_DB` | `app` | PostgreSQL database name |
| `POSTGRES_USER` | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `ACCESS_TOKEN_LIFETIME_MINUTES` | `30` | JWT access token lifetime in minutes |
| `REFRESH_TOKEN_LIFETIME_DAYS` | `1` | JWT refresh token lifetime in days |

## Project Structure

```
django-docker-template/
├── .env.example                        # Environment variable template
├── .github/workflows/ci.yml           # GitHub Actions CI pipeline
├── docker-compose.yml                  # Docker Compose services
├── prometheus.yml                      # Prometheus scrape config
└── src/
    ├── Dockerfile                      # Multi-stage build with uv
    ├── pyproject.toml                  # Dependencies and tool config
    ├── uv.lock                         # Locked dependencies
    ├── manage.py
    ├── conftest.py                     # Shared pytest fixtures
    ├── main/
    │   ├── settings.py                 # Env-driven Django settings
    │   ├── logging.py                  # LOGGING dict config
    │   ├── urls.py                     # Root URL routing
    │   ├── wsgi.py
    │   └── asgi.py
    ├── accounts/
    │   ├── models.py                   # CustomUser (email=USERNAME_FIELD)
    │   ├── managers.py                 # CustomUserManager
    │   ├── serializers.py              # User/Group serializers
    │   ├── views.py                    # UserViewSet, GroupViewSet
    │   ├── permissions.py              # IsAdmin, IsAdminOrOperator
    │   ├── urls.py                     # DRF router
    │   ├── admin.py                    # Django admin config
    │   ├── management/commands/
    │   │   ├── setup_groups.py         # Create default groups
    │   │   └── test_integration.py     # Integration test suite
    │   └── tests/                      # Unit tests
    ├── health/
    │   ├── views.py                    # /api/health/ endpoint
    │   └── tests/
    └── logging_utils/
        ├── formatters.py               # JSONFormatter
        ├── filters.py                  # PasswordRedactionFilter
        └── tests/
```

## CI/CD

GitHub Actions runs three jobs on every push and pull request:

1. **Lint** — `ruff check` and `ruff format --check`
2. **Test** — `pytest` with a PostgreSQL 17 service container
3. **Integration** — Full Docker Compose stack with migrations, group setup, integration tests, health check, and Prometheus verification

## License

This project is provided as a template. See [LICENSE](LICENSE) for details.
