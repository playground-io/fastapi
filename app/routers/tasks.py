"""HTTP endpoints for creating, reading, updating, and deleting tasks.

An APIRouter is a smaller collection of endpoints that can be attached to the
main application. Keeping task endpoints together makes the project easier to
extend with other resources, such as users or lessons.
"""

# ``Annotated`` attaches FastAPI metadata to an ordinary Python type hint.
from typing import Annotated

# APIRouter groups routes. Depends requests a dependency. HTTPException creates
# an HTTP error response. Query describes/validates URL query parameters.
# Response lets a route return an intentionally empty response. ``status``
# contains named HTTP status codes.
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

# ``select`` builds a SQL query in SQLAlchemy's modern Python API.
from sqlalchemy import select

# A Session is the unit of work used to read/write database objects.
from sqlalchemy.orm import Session

# Import the dependency, database model, and input/output API schemas.
from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskRead, TaskUpdate

# This router contributes /tasks to each route and groups routes as "tasks"
# in the automatically generated OpenAPI documentation.
router = APIRouter(prefix="/tasks", tags=["tasks"])

# This reusable type means "a SQLAlchemy Session supplied by get_db".
# It is not a value supplied in the URL or JSON body: FastAPI creates it by
# running the get_db dependency for each request.
DatabaseSession = Annotated[Session, Depends(get_db)]


# Register the next function as GET /api/tasks. The /api part is added when
# main.py includes this router; the empty route path adds no extra segment.
# ``response_model`` filters/validates each returned item as a TaskRead schema.
@router.get("", response_model=list[TaskRead])
def list_tasks(
    # FastAPI sees DatabaseSession and obtains it from the get_db dependency.
    db: DatabaseSession,
    # Query parameters are values after ? in the URL. ``None`` means no
    # completion filter was requested; FastAPI parses true/false into bool.
    completed: Annotated[bool | None, Query()] = None,
    # ``q`` is optional title-search text. If present, validate its length.
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    # ``offset`` skips this many matching rows. It cannot be negative.
    offset: Annotated[int, Query(ge=0)] = 0,
    # ``limit`` caps the number of returned rows, and cannot exceed 100.
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Task]:
    """List matching tasks and return only the requested page.

    The SQLAlchemy statement is built up before it is executed. This lets each
    optional filter be added only when the client asks for it.
    """
    # Begin a SELECT query for Task rows. Sort newest first; ID breaks ties
    # deterministically when two rows have the same recorded creation time.
    statement = select(Task).order_by(Task.created_at.desc(), Task.id.desc())

    # ``is not None`` is important because False is itself a valid filter:
    # completed=false must not be mistaken for "no filter".
    if completed is not None:
        statement = statement.where(Task.completed == completed)

    # Search titles without case sensitivity where supported by the database.
    # The % signs mean any sequence of characters may appear around the query.
    if q is not None:
        statement = statement.where(Task.title.ilike(f"%{q}%"))

    # Apply paging in the database instead of fetching every matching row.
    statement = statement.offset(offset).limit(limit)

    # Execute the query, extract Task objects from the result, and materialize
    # them as a list. FastAPI then converts each object through TaskRead.
    return list(db.scalars(statement).all())


# POST sends data to create a resource. Return 201 Created on success and use
# TaskRead as the documented and validated shape of the response.
@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(payload: TaskCreate, db: DatabaseSession) -> Task:
    """Create one task from a validated JSON request body.

    FastAPI constructs ``payload`` from the request JSON. If it does not match
    TaskCreate (for example, an empty title), FastAPI returns 422 before calling
    this function.
    """
    # Create a Python ORM object from the client-controlled fields only.
    task = Task(title=payload.title, description=payload.description)

    # Stage the new object in this session; this alone has not saved it yet.
    db.add(task)

    # Send the insert to the database and commit the transaction permanently.
    db.commit()

    # Load database-generated values such as the primary key back onto task.
    db.refresh(task)

    # FastAPI uses the response_model to turn this ORM object into public JSON.
    return task


# A value inside braces in a route path is a path parameter.
@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DatabaseSession) -> Task:
    """Fetch one task by its ID, or report that it does not exist.

    The ``int`` type hint asks FastAPI to parse the URL segment as an integer.
    """
    # ``Session.get`` looks up a row by its primary key (the task ID).
    task = db.get(Task, task_id)

    # Missing data is a normal API condition, so respond with a clear 404.
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Return the ORM object; response_model turns it into TaskRead JSON.
    return task


# PATCH changes an existing resource; the JSON body is checked against
# TaskUpdate before this function is entered.
@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: DatabaseSession) -> Task:
    """Change a task's completion state and return the updated task."""
    # First find the existing row. A PATCH must not invent a new task.
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Update the in-memory ORM object; SQLAlchemy tracks this assignment.
    task.completed = payload.completed

    # Persist the change in a database transaction.
    db.commit()

    # Refresh in case the database modified any values during the update.
    db.refresh(task)
    return task


# DELETE removes a resource. HTTP 204 means success with no response content.
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DatabaseSession) -> Response:
    """Delete one task, or return 404 if the requested ID is unknown."""
    # Look up the row before trying to delete it.
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Mark this row for deletion in the current session.
    db.delete(task)

    # Commit performs the SQL DELETE in the database.
    db.commit()

    # A 204 response has no JSON body, so return a plain empty Response.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
