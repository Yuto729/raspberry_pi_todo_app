"""Pydantic models for task API."""

from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""

    TODO = "todo"
    DONE = "done"
    ARCHIVED = "archived"


class TaskCreate(BaseModel):
    """Request model for creating a task."""

    title: str = Field(..., min_length=1, max_length=500)


class TaskUpdate(BaseModel):
    """Request model for updating a task."""

    title: str | None = Field(None, min_length=1, max_length=500)
    status: TaskStatus | None = None


class TaskResponse(BaseModel):
    """Response model for a task."""

    id: str
    title: str
    status: TaskStatus
    created_at: int
    updated_at: int


class TaskListResponse(BaseModel):
    """Response model for task list."""

    tasks: list[TaskResponse]
    count: int
