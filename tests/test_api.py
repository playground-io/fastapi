"""Test API behavior through HTTP without using the developer's real database.

These are integration tests: they send requests through FastAPI's application
and check the observable HTTP responses rather than calling route functions
directly.
"""

# A generator return type documents that the fixture yields a client and then
# runs cleanup after the test using it has finished.
from collections.abc import Generator

# pytest supplies fixtures and test discovery; TestClient sends in-process
# requests to the ASGI app without starting a real network server.
import pytest
from fastapi.testclient import TestClient

# SQLAlchemy makes a separate in-memory SQLite database for these tests.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import the application to override its database engine during startup.
from app import main
from app.database import get_db


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Yield a test client connected to a clean, temporary database.

    pytest runs the setup before ``yield`` and the cleanup after the test ends,
    even if an assertion fails.
    """
    # The empty SQLite URL creates a temporary in-memory database, not app.db.
    test_engine = create_engine(
        "sqlite://",
        # SQLite's thread check must be disabled for TestClient's request thread.
        connect_args={"check_same_thread": False},
        # A single shared connection keeps the in-memory database alive while
        # the test client makes multiple requests.
        poolclass=StaticPool,
    )

    # Create sessions bound to this test-only engine. These options mirror the
    # real app's sessions so tests behave like normal route calls.
    test_sessions = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    # This replacement dependency yields sessions connected to the test DB.
    # Its shape matches the application's original get_db dependency.
    def override_get_db():
        with test_sessions() as session:
            yield session

    # The application lifespan creates tables using main.engine, so replace
    # that reference before TestClient starts the application.
    monkeypatch.setattr(main, "engine", test_engine)

    # FastAPI checks this mapping when it sees Depends(get_db) in a route.
    # Use the test dependency instead of opening the developer database.
    main.app.dependency_overrides[get_db] = override_get_db
    try:
        # Entering the client context starts the app lifespan and creates tables.
        with TestClient(main.app) as test_client:
            # pytest injects this client into the test function.
            yield test_client
    finally:
        # Remove overrides so they cannot affect another test.
        main.app.dependency_overrides.clear()
        # Close database connections after all requests are complete.
        test_engine.dispose()


def test_health_check(client: TestClient) -> None:
    """The basic route should answer successfully with its documented JSON."""
    # Make an HTTP GET request to the in-process API.
    response = client.get("/health")

    # Check both the HTTP status and returned JSON value.
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_task_crud_and_completion_filter(client: TestClient) -> None:
    """Create, update, filter, and delete a task using HTTP requests."""
    # POST sends JSON; surrounding spaces demonstrate schema string trimming.
    created = client.post(
        "/api/tasks",
        json={"title": "  Learn FastAPI  ", "description": "Read the docs."},
    )

    # A successful creation uses 201 Created and returns the saved task.
    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Learn FastAPI"
    assert task["completed"] is False

    # Use the generated ID in the URL and PATCH only the completion field.
    updated = client.patch(f"/api/tasks/{task['id']}", json={"completed": True})
    assert updated.status_code == 200
    assert updated.json()["completed"] is True

    # Query parameters go in params=; the client encodes them into the URL.
    assert client.get("/api/tasks", params={"completed": True}).json() == [
        updated.json()
    ]

    # DELETE succeeds with 204 and leaves no task in the collection.
    deleted = client.delete(f"/api/tasks/{task['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/tasks").json() == []


def test_task_detail_search_and_pagination(client: TestClient) -> None:
    """Exercise the detail route and optional query/pagination parameters."""
    # Make two resources so search and pagination have something to distinguish.
    first = client.post("/api/tasks", json={"title": "Learn FastAPI"})
    second = client.post("/api/tasks", json={"title": "Read about Python"})

    # Verify setup succeeded before relying on either response body below.
    assert first.status_code == second.status_code == 201
    first_task = first.json()

    # A path parameter selects one task by ID.
    assert client.get(f"/api/tasks/{first_task['id']}").json() == first_task

    # q searches titles without matching case, returning the relevant task.
    assert [task["title"] for task in client.get(
        "/api/tasks", params={"q": "fastapi"}
    ).json()] == ["Learn FastAPI"]

    # Newest tasks come first, so offset=1 skips the second task and shows first.
    assert client.get("/api/tasks", params={"offset": 1, "limit": 1}).json() == [
        first_task
    ]


def test_validation_and_missing_task_errors(client: TestClient) -> None:
    """Check that invalid input and missing resources produce useful HTTP errors."""
    # Whitespace is stripped from the title, leaving an invalid empty string.
    invalid_body = client.post("/api/tasks", json={"title": "   "})

    # The maximum allowed page size is 100, so 101 is rejected by Query.
    invalid_query = client.get("/api/tasks", params={"limit": 101})

    # No task with this ID exists in the clean test database.
    missing_task = client.get("/api/tasks/999")

    # FastAPI reports invalid body/query data with 422 Unprocessable Content.
    assert invalid_body.status_code == 422
    assert invalid_query.status_code == 422

    # The route reports a missing database row with 404 Not Found.
    assert missing_task.status_code == 404
    assert missing_task.json() == {"detail": "Task not found"}
