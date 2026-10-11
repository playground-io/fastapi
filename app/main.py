"""Create the FastAPI application and demonstrate a very simple route.

This is the application's entry point: the ASGI server imports the variable
named ``app`` from this module when started with ``uvicorn app.main:app``.
"""

# ``asynccontextmanager`` turns an async generator into a resource lifecycle
# manager. FastAPI uses it for work that should happen at startup and shutdown.
from contextlib import asynccontextmanager

# ``FastAPI`` is the class used to create the web application object.
from fastapi import FastAPI

# ``Base`` describes all ORM tables, and ``engine`` connects to the database.
from app.database import Base, engine

# Importing the router makes its endpoints available for registration below.
from app.routers.tasks import router as tasks_router


# FastAPI calls this function when the application starts and stops.
@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare the local database before accepting requests.

    The value before ``yield`` runs at startup; code after it would run at
    shutdown. The underscore means this function receives the app argument but
    does not need to use it.
    """
    # Import the model module so SQLAlchemy registers Task in Base.metadata.
    # This local import also avoids making app startup depend on route imports.
    from app import models  # noqa: F401

    # Create tables that do not exist yet. This is convenient for a tutorial,
    # but does not change existing tables; real projects generally use migrations.
    Base.metadata.create_all(bind=engine)

    # Hand control back to FastAPI. The application now accepts requests.
    yield


# Instantiate the application. FastAPI uses these values in generated docs.
app = FastAPI(
    title="Learn FastAPI",
    description="A beginner-friendly API that grows from simple routes to CRUD.",
    version="1.0.0",
    # Register the startup/shutdown work defined above.
    lifespan=lifespan,
)

# Mount the tasks router. Its own prefix is /tasks, and this prefix adds /api,
# so a router route such as "" becomes the full URL /api/tasks.
app.include_router(tasks_router, prefix="/api")


# ``@app.get`` registers the function below as a handler for HTTP GET /health.
# ``tags`` groups this introductory endpoint in the interactive API docs.
@app.get("/health", tags=["basics"])
def health_check() -> dict[str, str]:
    """Return a simple status object to show that the server is responding.

    The return annotation says this function returns a dictionary with string
    keys and string values. FastAPI converts the Python dictionary to JSON.
    """
    # FastAPI turns this into the JSON response {"status": "ok"}.
    return {"status": "ok"}
