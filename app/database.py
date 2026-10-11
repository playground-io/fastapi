"""Connect the application to a database and manage SQLAlchemy sessions.

This module is the shared database setup. Models import ``Base`` so they can
describe tables, while routes use ``get_db`` to work with a session per request.
"""

# ``os`` reads environment variables supplied by the shell or deployment.
import os

# ``Generator`` describes a function that returns values one at a time with
# ``yield``. FastAPI understands this pattern for dependencies with cleanup.
from collections.abc import Generator

# ``create_engine`` builds SQLAlchemy's database connection manager.
from sqlalchemy import create_engine

# ``DeclarativeBase`` is the parent for table models. ``Session`` represents a
# conversation with the database. ``sessionmaker`` creates those sessions.
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Read the database address from the environment. If it is not set, keep the
# database in a file named app.db in the directory where the server is started.
# A URL such as sqlite:///./app.db tells SQLAlchemy which database/driver to use.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# The engine is the long-lived object that knows how to connect to the database.
engine = create_engine(
    # Use the selected URL rather than hard-coding a database in route code.
    DATABASE_URL,
    # SQLite normally restricts a connection to the thread that opened it.
    # A web server can run request code in another thread, so disable that
    # restriction for SQLite only. Other database drivers need no such option.
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)

# ``sessionmaker`` is a factory: call it to get a new Session when needed.
# ``autoflush=False`` avoids sending pending changes to the database merely
# because a query was run. ``expire_on_commit=False`` keeps saved object values
# available after commit, so routes can return them without reloading first.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared parent class that makes subclasses into SQLAlchemy table models.

    For example, ``class Task(Base)`` registers the Task table with
    ``Base.metadata``. Metadata is SQLAlchemy's collection of known table
    descriptions.
    """


def get_db() -> Generator[Session, None, None]:
    """Give one route a session, then close it even if the route raises an error.

    FastAPI sees ``yield`` and treats this function as a dependency with setup
    (before yield) and cleanup (after yield). The ``with`` statement guarantees
    that the session is closed when FastAPI finishes handling the request.
    """
    # Create a session just for this use; do not share it between requests.
    with SessionLocal() as session:
        # Pause here and provide this session to the endpoint that requested it.
        yield session
