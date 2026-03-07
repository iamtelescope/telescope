# Telescope

Telescope is a log exploration tool providing a unified interface for querying logs from ClickHouse, Docker, Kubernetes, and StarRocks data sources. Built with Django (backend) and Vue.js (frontend).

## Tech Stack

- **Backend**: Python 3.12, Django 5.1, Django REST Framework, Gunicorn
- **Frontend**: Vue.js 3 (Vue CLI, not Vite), PrimeVue, Tailwind CSS, Monaco Editor, vue-router, Pinia
- **Query Language**: FlyQL (custom, from `iamtelescope/flyql`)
- **Auth**: django-allauth (GitHub OAuth, Okta SAML)
- **Database**: SQLite (default), PostgreSQL, MySQL supported

## Project Structure

- `backend/` — Django application (telescope app, DRF API, fetchers, RBAC)
- `ui/` — Vue.js frontend (components, Pinia stores, composables, sdk/)
- `dev/` — Local development config (`config.yaml`) and SQLite DB
- `helm/` — Kubernetes Helm charts

## Development Commands

```bash
make venv              # Create Python virtualenv at backend/.venv
make update-venv       # Update dependencies in existing virtualenv
make run-backend       # Run Django dev server on port 8000
make run-ui            # Run Vue dev server on port 8080 (sets VUE_APP_BACKEND_URL automatically)

cd backend && make fmt   # Format Python code (black)
cd backend && make test  # Run tests (pytest)
cd ui && make fmt        # Format frontend code (prettier)
```

## Code Formatting

- **Python**: black with default settings
- **Frontend** (prettier, transitive dep — not in devDependencies): no semicolons, single quotes, print width 120, tab width 4

## Architecture

- **Fetchers**: `backend/telescope/fetchers/` - each data source type (clickhouse, docker, kubernetes, starrocks) implements `BaseFetcher`
- **FlyQL**: custom query language parsed by the `flyql` library
- **RBAC**: `backend/telescope/rbac/` - hierarchical roles (Admin, Owner, Editor, Viewer, etc.) with Global, Connection, and Source level bindings
- **API routes**: `/api/v1/` (external API), `/ui/v1/` (frontend-facing API)
- **Config**: YAML-based, loaded via `TELESCOPE_CONFIG_FILE` env var (dev default: `dev/config.yaml`)
- **Production**: frontend built into Django static files, served via whitenoise

## Database

- Default: SQLite (`dev/db.sqlite3` for local dev)
- Migrations: `backend/telescope/migrations/`
- Run migrations: `cd backend && python manage.py migrate`

## Related Repositories

Check if these sibling repos are available locally. If not, ask the user where they are or clone them:
- `../docs-telescope` — Documentation site (Astro/Starlight). Feature docs, concepts, and configuration. Repo: https://github.com/iamtelescope/telescope-docs
- `../flyql` — FlyQL query language library used for query parsing. Repo: https://github.com/iamtelescope/flyql
