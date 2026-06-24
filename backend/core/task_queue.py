"""
Task Queue — Async task processing with priority, retries, and status tracking.
Modules can submit tasks to be processed in order of priority.
"""

import time
import json
import logging
import asyncio
import uuid
from enum import Enum
from pathlib import Path
from collections import deque
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger("mj.task_queue")

QUEUE_FILE = Path(__file__).parent.parent / "task_queue.json"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """A queued task."""

    def __init__(self, name: str, handler: str, params: Dict = None,
                 priority: int = 5, max_retries: int = 1, submitted_by: str = "system"):
        self.task_id = uuid.uuid4().hex[:8]
        self.name = name
        self.handler = handler  # module name or callable reference
        self.params = params or {}
        self.priority = priority  # 1=highest, 10=lowest
        self.max_retries = max_retries
        self.retries = 0
        self.status = TaskStatus.PENDING
        self.submitted_by = submitted_by
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "handler": self.handler,
            "params": self.params,
            "priority": self.priority,
            "status": self.status.value,
            "submitted_by": self.submitted_by,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


class TaskQueue:
    """
    Priority task queue with async processing.
    Tasks are sorted by priority (lower number = higher priority).
    """

    def __init__(self, max_history: int = 100):
        self._queue: List[Task] = []
        self._history: deque = deque(maxlen=max_history)
        self._handlers: Dict[str, Callable] = {}
        self._processing = False
        self._current_task: Optional[Task] = None
        self._stats = {"submitted": 0, "completed": 0, "failed": 0, "cancelled": 0}

    def register_handler(self, name: str, handler: Callable):
        """Register a task handler by name."""
        self._handlers[name] = handler

    def submit(self, name: str, handler: str, params: Dict = None,
               priority: int = 5, max_retries: int = 1, submitted_by: str = "system") -> Task:
        """Submit a task to the queue. Returns the Task object."""
        task = Task(name, handler, params, priority, max_retries, submitted_by)
        self._queue.append(task)
        self._queue.sort(key=lambda t: (t.priority, t.created_at))
        self._stats["submitted"] += 1
        logger.info(f"Task queued: {task.name} (id={task.task_id}, priority={task.priority})")
        return task

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        for task in self._queue:
            if task.task_id == task_id and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.completed_at = time.time()
                self._queue.remove(task)
                self._history.append(task.to_dict())
                self._stats["cancelled"] += 1
                return True
        return False

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get task info by ID."""
        # Check queue
        for task in self._queue:
            if task.task_id == task_id:
                return task.to_dict()
        # Check current
        if self._current_task and self._current_task.task_id == task_id:
            return self._current_task.to_dict()
        # Check history
        for entry in self._history:
            if entry["task_id"] == task_id:
                return entry
        return None

    async def process_next(self) -> Optional[dict]:
        """Process the next task in the queue."""
        if not self._queue:
            return None
        if self._processing:
            return {"status": "busy", "current": self._current_task.to_dict() if self._current_task else None}

        task = self._queue.pop(0)
        self._current_task = task
        self._processing = True
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        try:
            handler = self._handlers.get(task.handler)
            if not handler:
                raise ValueError(f"No handler registered for '{task.handler}'")

            if asyncio.iscoroutinefunction(handler):
                result = await handler(**task.params)
            else:
                result = handler(**task.params)

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self._stats["completed"] += 1
            logger.info(f"Task completed: {task.name} ({task.completed_at - task.started_at:.1f}s)")

        except Exception as e:
            task.retries += 1
            if task.retries < task.max_retries:
                # Re-queue for retry
                task.status = TaskStatus.PENDING
                task.started_at = None
                self._queue.append(task)
                self._queue.sort(key=lambda t: (t.priority, t.created_at))
                logger.warning(f"Task {task.name} failed, retrying ({task.retries}/{task.max_retries}): {e}")
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = time.time()
                self._stats["failed"] += 1
                logger.error(f"Task failed permanently: {task.name}: {e}")

        finally:
            self._processing = False
            self._current_task = None
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                self._history.append(task.to_dict())

        return task.to_dict()

    async def process_all(self) -> List[dict]:
        """Process all tasks in the queue sequentially."""
        results = []
        while self._queue:
            result = await self.process_next()
            if result:
                results.append(result)
        return results

    def get_queue(self) -> List[dict]:
        """Get all pending tasks."""
        return [t.to_dict() for t in self._queue]

    def get_history(self, limit: int = 50) -> List[dict]:
        """Get completed/failed task history."""
        return list(self._history)[-limit:]

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            **self._stats,
            "queue_length": len(self._queue),
            "is_processing": self._processing,
            "current_task": self._current_task.to_dict() if self._current_task else None,
        }

    def clear_queue(self) -> int:
        """Cancel all pending tasks."""
        count = len(self._queue)
        for task in self._queue:
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            self._history.append(task.to_dict())
        self._queue.clear()
        self._stats["cancelled"] += count
        return count


# Singleton
task_queue = TaskQueue()
