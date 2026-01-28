"""Database package."""

from .client import (
    create_task,
    delete_task,
    get_all_tasks,
    get_task_by_id,
    init_db,
    update_task,
)

__all__ = [
    "init_db",
    "create_task",
    "get_all_tasks",
    "get_task_by_id",
    "update_task",
    "delete_task",
]
