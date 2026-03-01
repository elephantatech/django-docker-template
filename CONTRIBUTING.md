# Contributing

Thanks for your interest in contributing to this project. This guide covers the workflow, standards, and rules for making contributions.

## Getting Started

1. Fork the repository and clone your fork:

```bash
git clone https://github.com/<your-username>/django-docker-template.git
cd django-docker-template
```

2. Install dependencies:

```bash
cd src
uv sync --all-extras
```

3. Copy the environment file and start services:

```bash
cp .env.example .env
docker compose up -d db
```

4. Run migrations and verify tests pass:

```bash
uv run python manage.py migrate
uv run pytest -v
```

## Development Workflow

1. Create a branch from `master`:

```bash
git checkout -b feature/your-feature-name
```

2. Make your changes.

3. Run linting and tests before committing:

```bash
uv run ruff check .
uv run ruff format .
uv run pytest -v
```

4. Commit with a clear, descriptive message:

```bash
git commit -m "Add user email validation to registration endpoint"
```

5. Push your branch and open a pull request against `master`.

## Code Standards

### Style

- **Formatter/linter**: [ruff](https://docs.astral.sh/ruff/). All code must pass `ruff check` and `ruff format --check` with zero errors.
- **Line length**: 99 characters max.
- **Imports**: Sorted by ruff's isort rules. Standard library first, third-party second, local third.
- **Quotes**: Double quotes for strings.

### Code Guidelines

- Follow existing patterns in the codebase. Look at similar files before writing new code.
- Use environment variables for all configuration that changes between environments. Never hardcode secrets, database URLs, or host-specific values.
- Use Django's `get_user_model()` instead of importing the `CustomUser` model directly in app code outside of `accounts`.
- Write permission checks using the custom permission classes in `accounts/permissions.py`. Do not use inline permission logic in views.
- Keep views thin. Business logic belongs in serializers, model methods, or dedicated service functions.

### Django Conventions

- All new models must set `default_auto_field = "django.db.models.BigAutoField"` in their app config.
- Use `AUTH_USER_MODEL` setting — never import the user model directly.
- New apps must be added to `INSTALLED_APPS` in `main/settings.py`.
- Database changes require a migration. Run `uv run python manage.py makemigrations` and include the migration file in your commit.

## Testing

### Requirements

- All new features must include tests.
- All bug fixes must include a test that reproduces the bug.
- Tests must pass before a pull request will be reviewed.
- Aim for test names that describe the expected behavior: `test_readonly_cannot_delete_user`, not `test_delete_3`.

### Running Tests

```bash
# Unit tests (local, uses SQLite)
cd src
uv run pytest -v

# Unit tests (Docker Compose, uses PostgreSQL)
docker compose up -d db
docker compose run --rm web /app/.venv/bin/pytest -v

# Integration tests (full Docker Compose stack)
docker compose up -d --build
docker compose exec web /app/.venv/bin/python manage.py migrate
docker compose exec web /app/.venv/bin/python manage.py setup_groups
docker compose exec web /app/.venv/bin/python manage.py test_integration
```

### Test Organization

- Place tests in the `tests/` directory within each app.
- Use one test file per concern: `test_models.py`, `test_views_users.py`, `test_permissions.py`, etc.
- Use `conftest.py` for shared fixtures. Prefer fixtures from `conftest.py` over creating test data inline.
- Use `factory-boy` factories (defined in `conftest.py`) to create test objects. Do not use `Model.objects.create()` unless testing the manager itself.

### Test Structure

```python
@pytest.mark.django_db
class TestUserCreate:
    def test_admin_can_create_user(self, admin_client):
        response = admin_client.post("/api/users/", {...}, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_operator_cannot_create_user(self, operator_client):
        response = operator_client.post("/api/users/", {...}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
```

## Pull Request Rules

### Before Submitting

- [ ] Branch is up to date with `master`.
- [ ] `uv run ruff check .` passes with zero errors.
- [ ] `uv run ruff format --check .` passes with zero errors.
- [ ] `uv run pytest -v` passes with all tests green.
- [ ] New migrations are included if models changed.
- [ ] No secrets, credentials, or `.env` files are committed.

### PR Guidelines

- Keep pull requests focused. One feature or fix per PR.
- Write a clear title and description. Explain **what** changed and **why**.
- Reference related issues with `Closes #123` or `Fixes #123`.
- If your PR introduces a new API endpoint, include example request/response in the description.
- If your PR changes permissions or access control, explicitly list which roles are affected.

### Review Process

- All PRs require at least one review before merging.
- CI must pass (lint, tests, integration) before merging.
- Reviewers may request changes. Address all feedback before re-requesting review.
- Squash merge is preferred for single-feature branches.

## Adding New Features

### New API Endpoint

1. Add the view to the appropriate app's `views.py`.
2. Add permission classes. Use existing ones from `accounts/permissions.py` or create new ones if needed.
3. Register the URL in the app's `urls.py` (or add to the DRF router).
4. Add serializers for request/response handling.
5. Write tests covering all permission groups (Admin, Operator, ReadOnly) and unauthenticated access.
6. Update the README endpoint table.

### New App

1. Create the app directory under `src/` with `__init__.py`, `apps.py`, `views.py`, `urls.py`.
2. Add the app to `INSTALLED_APPS` in `main/settings.py`.
3. Include the app's URLs in `main/urls.py`.
4. Create a `tests/` directory with `__init__.py` and test files.
5. Run `uv run python manage.py makemigrations` if the app has models.

### New Dependency

1. Add the dependency to `pyproject.toml` under `[project.dependencies]` (or `[project.optional-dependencies.dev]` for dev-only).
2. Run `uv sync` to update `uv.lock`.
3. Commit both `pyproject.toml` and `uv.lock`.

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests.
- Include steps to reproduce for bugs.
- Include the expected and actual behavior.
- Include relevant logs or error messages.
