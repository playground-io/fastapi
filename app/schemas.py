"""Define the data shapes accepted and returned by the HTTP API.

Pydantic models validate Python data at the application boundary. FastAPI also
uses them to describe request bodies and responses in the interactive docs.
"""

# The read schema needs datetime because the ORM model stores a creation time.
from datetime import datetime

# ``BaseModel`` is the parent for validated schemas.
# ``ConfigDict`` changes how a schema behaves, and ``Field`` adds constraints.
from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    """The JSON fields a client may send to create a task.

    This is separate from the database model: API clients should only be allowed
    to provide the fields needed to create a task, not its generated ID/time.
    """

    # Reject unexpected keys and trim leading/trailing whitespace from strings.
    # For example, "  Learn FastAPI  " becomes "Learn FastAPI".
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # A title is required, must not be empty, and must fit the table's limit.
    title: str = Field(min_length=1, max_length=200)

    # Description may be omitted or explicitly null. If it is text, cap its
    # length so clients cannot submit arbitrarily large descriptions.
    description: str | None = Field(default=None, max_length=2000)


class TaskUpdate(BaseModel):
    """The fields accepted when changing a task with PATCH.

    PATCH means a partial update in general; this simple learning endpoint
    currently requires exactly the completion field it knows how to update.
    """

    # Do not silently accept misspelled or unsupported fields.
    model_config = ConfigDict(extra="forbid")

    # The client must send true or false, for example {"completed": true}.
    completed: bool


class TaskRead(BaseModel):
    """The public task shape sent back to API clients.

    Keeping a separate read schema means database-only details are not exposed
    accidentally, and the API response remains an explicit contract.
    """

    # A route returns a SQLAlchemy Task object. This setting lets Pydantic read
    # its attributes (task.id, task.title, etc.) to build this response object.
    model_config = ConfigDict(from_attributes=True)

    # These annotations describe the JSON response fields and their value types.
    id: int
    title: str
    description: str | None
    completed: bool
    created_at: datetime
