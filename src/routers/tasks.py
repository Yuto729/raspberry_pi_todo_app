"""Task API router."""

import time
from html import escape

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from ulid import ULID

from ..db import (
    create_task,
    delete_task,
    get_all_tasks,
    get_task_by_id,
    update_task,
)
from ..models import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# =============================================================================
# Helper Functions
# =============================================================================


def render_task_item(task: dict) -> str:
    """Render a single task as HTML."""
    title = escape(task["title"])
    task_id = task["id"]
    return f"""
    <li id="task-{task_id}" class="task-item">
        <span class="task-title">{title}</span>
        <button
            class="complete-btn"
            hx-patch="/api/tasks/{task_id}/htmx/complete"
            hx-target="#task-{task_id}"
            hx-swap="outerHTML"
        ></button>
    </li>
    """


def render_task_list(tasks: list[dict]) -> str:
    """Render task list as HTML."""
    if not tasks:
        return '<li class="empty-message">タスクがありません</li>'
    return "".join(render_task_item(task) for task in tasks)


# =============================================================================
# HTMX Endpoints (HTML Fragments) - Must be defined BEFORE /{task_id} routes
# =============================================================================


@router.get("/htmx", response_class=HTMLResponse)
def list_tasks_htmx(status: TaskStatus | None = None):
    """Get all tasks as HTML fragment."""
    status_value = status.value if status else None
    tasks = get_all_tasks(status=status_value)
    return render_task_list(tasks)


@router.post("/htmx", response_class=HTMLResponse)
def create_task_htmx(title: str = Form(...)):
    """Create a task and return HTML fragment."""
    task_id = str(ULID())
    created_at = int(time.time())
    task = create_task(task_id, title, created_at)
    return render_task_item(task)


# =============================================================================
# REST API Endpoints (JSON)
# =============================================================================


@router.get("", response_model=TaskListResponse)
def list_tasks(status: TaskStatus | None = None):
    """Get all tasks, optionally filtered by status."""
    status_value = status.value if status else None
    tasks = get_all_tasks(status=status_value)
    return TaskListResponse(
        tasks=[TaskResponse(**task) for task in tasks],
        count=len(tasks),
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    """Get a task by ID."""
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return TaskResponse(**task)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(task_data: TaskCreate):
    """Create a new task."""
    task_id = str(ULID())
    created_at = int(time.time())
    task = create_task(task_id, task_data.title, created_at)
    return TaskResponse(**task)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task_endpoint(task_id: str, task_data: TaskUpdate):
    """Update a task's title and/or status."""
    existing = get_task_by_id(task_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    updated_at = int(time.time())
    status_value = task_data.status.value if task_data.status else None
    task = update_task(task_id, task_data.title, status_value, updated_at)
    return TaskResponse(**task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_endpoint(task_id: str):
    """Delete a task."""
    if not delete_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


# =============================================================================
# HTMX Endpoints with task_id (must be after static /htmx routes)
# =============================================================================


@router.patch("/{task_id}/htmx/complete", response_class=HTMLResponse)
def complete_task_htmx(task_id: str):
    """Mark a task as done and return empty (remove from list)."""
    existing = get_task_by_id(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    updated_at = int(time.time())
    update_task(task_id, None, "done", updated_at)
    return ""


@router.delete("/{task_id}/htmx", response_class=HTMLResponse)
def delete_task_htmx(task_id: str):
    """Delete a task and return empty."""
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return ""
