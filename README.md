# Learn FastAPI

A small, documented API for learning FastAPI from the basics up. It uses
Pydantic for input/output validation, SQLAlchemy 2 for SQLite persistence, and
pytest to exercise the API without touching the development database.

## Requirements

- Python 3.10+
- pip

## Run the API

From this directory:

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the project dependencies and start the development server:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit <http://127.0.0.1:8000/docs> to try the endpoints interactively.
FastAPI also provides ReDoc at <http://127.0.0.1:8000/redoc>.

## Learn in stages

1. **Application and route** — `app/main.py` creates the FastAPI application.
   `GET /health` returns a Python dictionary, which FastAPI serializes as JSON.
2. **Path parameters** — `GET /api/tasks/{task_id}` uses an `int` type hint.
   FastAPI converts and validates the URL value before calling the endpoint.
3. **Request bodies and schemas** — `POST /api/tasks` accepts `TaskCreate`.
   Pydantic validates the JSON and rejects unknown fields before route code runs.
4. **Response models and status codes** — the routes use `TaskRead` to describe
   their public response shape. Creating a task returns `201`; deleting one
   returns `204` with no body.
5. **Query parameters** — `GET /api/tasks` demonstrates optional completion and
   title filters, validated defaults, and bounded `offset`/`limit` pagination.
6. **Dependencies and persistence** — `DatabaseSession` in
   `app/routers/tasks.py` asks FastAPI to inject the `get_db` dependency.
   `app/database.py` opens a session for the request and closes it afterward.
7. **Routers** — task endpoints are grouped in `app/routers/tasks.py` using an
   `APIRouter`; `main.py` mounts them beneath `/api`.
8. **Errors** — missing task IDs raise `HTTPException` with a useful `404`.
   Invalid request data and query parameters receive FastAPI's standard `422`.
9. **Tests** — `tests/test_api.py` uses FastAPI's `TestClient` and overrides
   `get_db` with an in-memory SQLite database, keeping tests isolated.

## Try the API

Create a task:

```bash
curl -X POST http://127.0.0.1:8000/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Learn FastAPI","description":"Try the interactive docs"}'
```

Search and paginate:

```bash
curl 'http://127.0.0.1:8000/api/tasks?completed=false&q=FastAPI&offset=0&limit=5'
```

Use the `id` returned when creating a task to retrieve it, mark it complete, or
delete it:

```bash
curl http://127.0.0.1:8000/api/tasks/1
curl -X PATCH http://127.0.0.1:8000/api/tasks/1 \
  -H 'Content-Type: application/json' \
  -d '{"completed":true}'
curl -X DELETE http://127.0.0.1:8000/api/tasks/1
```

## Test and lint

```bash
python -m pip install -r requirements.txt
pytest
ruff check .
```

## Project structure

```text
fastapi/
├── app/
│   ├── routers/
│   │   └── tasks.py   # Endpoints, query params, dependencies, and HTTP errors
│   ├── database.py    # Engine, ORM base, and request-scoped sessions
│   ├── main.py        # Application setup, lifespan, and health route
│   ├── models.py      # SQLAlchemy table model
│   └── schemas.py     # Pydantic request and response models
├── tests/
│   └── test_api.py    # Isolated API integration tests
├── pyproject.toml     # pytest and Ruff settings
└── requirements.txt
```

The app creates missing SQLite tables at startup for easy local learning.
For production, use database migrations (for example, Alembic) rather than
relying on `create_all`, and add authentication and authorization before
exposing private data.
# fastapi
