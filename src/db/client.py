"""SQLite database operations for tasks."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DATABASE_PATH = Path(__file__).parent.parent.parent / "tasks.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with WAL mode enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'todo',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_created_at
            ON tasks(created_at)
        """)


def create_task(task_id: str, title: str, created_at: int) -> dict:
    """Create a new task."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, title, status, created_at, updated_at)
            VALUES (?, ?, 'todo', ?, ?)
            """,
            (task_id, title, created_at, created_at),
        )
    return get_task_by_id(task_id)


def get_all_tasks(status: str | None = None) -> list[dict]:
    """Get all tasks, optionally filtered by status."""
    with get_db() as conn:
        if status:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_task_by_id(task_id: str) -> dict | None:
    """Get a task by ID."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_task(
    task_id: str, title: str | None, status: str | None, updated_at: int
) -> dict | None:
    """Update a task's title and/or status."""
    with get_db() as conn:
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        updates.append("updated_at = ?")
        params.append(updated_at)
        params.append(task_id)

        conn.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            params,
        )
    return get_task_by_id(task_id)


def delete_task(task_id: str) -> bool:
    """Delete a task by ID."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0
