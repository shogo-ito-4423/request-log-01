from datetime import UTC, datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models import Priority, Status

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Assignee = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, Field(max_length=10000)]


class IssueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description = ""
    status: Status = Status.OPEN
    priority: Priority = Priority.MEDIUM
    assignee: Assignee | None = None


class IssueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    status: Status | None = None
    priority: Priority | None = None
    assignee: Assignee | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for name in self.model_fields_set - {"assignee"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class IssueRead(IssueCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        # SQLite returns naive datetimes; all writes in this application use UTC.
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
