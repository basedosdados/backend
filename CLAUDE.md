# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Base dos Dados backend — a Django + PostgreSQL API serving Brazil's largest public data platform. Exposes a GraphQL API (Graphene-Django) and a chatbot REST API (DRF + LangChain/LangGraph). Background tasks via Huey+Redis; full-text search via Elasticsearch+Haystack; payments via Stripe/dj-stripe.

## Commands

```bash
# Install
make install                      # poetry install
make install_precommit            # install pre-commit hooks

# Development
make run_local                    # makemigrations + migrate + runserver 0.0.0.0:8080
make run_docker                   # docker-compose up --build --force-recreate --detach

# Database
make migrations                   # python manage.py makemigrations
make migrate                      # python manage.py migrate
make loadfixture                  # python manage.py loadfixture fixture.json
make superuser

# Lint
make lint                         # poetry run lint (Ruff check + format)

# Tests
poetry run pytest                 # all tests
poetry run pytest backend/apps/api/v1/tests/  # specific directory
poetry run pytest -k "test_name"  # single test by name

# Docker helpers
make shell_docker                 # bash into api container
make logs_docker                  # tail logs
make stop_docker / make clean_docker
```

## Architecture

### Settings
- `backend/settings/base.py` — shared config, imported by all envs
- `backend/settings/local.py` — local dev (PostgreSQL via env vars, SMTP)
- `backend/settings/remote.py` — production/staging
- `pytest.ini` uses `DJANGO_SETTINGS_MODULE=backend.settings` (resolves to `base.py`)

### Django Apps (`backend/apps/`)

| App | Purpose |
|-----|---------|
| `account` | Custom user model (`Account`), roles (`BDRole`/`BDGroup`), registration tokens |
| `account_auth` | JWT authentication and authorization rules |
| `account_payment` | Stripe/dj-stripe integration |
| `api/v1` | Core data catalog: Dataset, Table, Column, ObservationLevel, Coverage, Area, Entity, etc. |
| `core` | Shared models (Metadata, TaskExecution), utility management commands |
| `chatbot` | Stub app; actual chatbot logic lives in the separate `chatbot/` package |
| `user_notifications` | Table-update notification subscriptions |

### GraphQL Auto-Generation

The GraphQL schema is **code-generated** from Django models via `backend/custom/graphql_auto.py`.

To expose a model in GraphQL:
1. Set `graphql_visible = True` on the model class (from `BaseModel`).
2. Control field exposure with `graphql_fields_whitelist`/`graphql_fields_blacklist`.
3. Control filtering with `graphql_filter_fields_whitelist` / `graphql_nested_filter_fields_whitelist`.
4. Set `graphql_query_decorator` (default: `anyone_required`) and `graphql_mutation_decorator` (default: `staff_member_required`) for auth.

The master schema is assembled in `backend/apps/schema.py`:
```python
schema = build_schema(
    applications=["account", "v1"],
    extra_queries=[APIQuery, PaymentQuery, UserNotificationQuery],
    extra_mutations=[AccountMutation, APIMutation, PaymentMutation, ...],
)
```

Manual queries/mutations (not auto-generated) live in each app's `graphql.py`.

### BaseModel (`backend/custom/model.py`)

All domain models inherit from `BaseModel` (abstract). Key attributes:
- UUID primary key, `created_at`/`updated_at` timestamps
- GraphQL visibility and field filtering class attributes
- `admin_url` property

### Key Patterns

- **M2M mutations**: use `commit=False` + `save_m2m()` to ensure M2M fields are saved (see recent commit history).
- **Ordered models**: `api/v1` uses `django-ordered-model` for column/table ordering; management commands `reorder_columns` and `reorder_tables` handle bulk reordering.
- **Model translation**: `django-modeltranslation` provides pt/en/es translations on selected fields.
- **Search**: Haystack + custom `AsciifoldingElasticSearchEngine`; indexes auto-update via signals.
- **Fixtures**: `loadfixture`/`dumpfixture` management commands wrap Django's fixture system with chunking support (`fixtures_chunks/`).

### GraphQL Endpoint

`/graphql/` — authenticated via `Bearer <JWT>` header. JWT obtained via `ObtainJSONWebToken` mutation.
