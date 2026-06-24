"""
Event System — System-wide event emitter/listener.
Tracks events like module_started, task_completed, error_occurred, etc.
Supports one-time listeners, event history, and event filtering.
"""

import time
import logging
import asyncio
from collections import defaultdict, deque
from typing import Callable, Optional, Dict, Any, List

logger = logging.getLogger("mj.events")

# Standard system events
EVENTS = {
    "system.startup": "System started",
    "system.shutdown": "System shutting down",
    "module.registered": "A module was registered",
    "module.executed": "A module finished execution",
    "module.error": "A module encountered an error",
    "task.queued": "A task was added to the queue",
    "task.started": "A task started processing",
    "task.completed": "A task completed",
    "task.failed": "A task failed",
    "memory.set": "Shared memory value set",
    "memory.expired": "Shared memory value expired",
    "chat.message": "New chat message",
    "chat.response": "AI response generated",
    "command.executed": "PC command executed",
}


class Event:
    """An event occurrence."""
    __slots__ = ("name", "source", "data", "timestamp", "event_id")
    _counter = 0

    def __init__(self, name: str, source: str = "system", data: Any = None):
        Event._counter += 1
        self.event_id = Event._counter
        self.name = name
        self.source = source
        self.data = data
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.event_id,
            "name": self.name,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class EventSystem:
    """
    Central event system for MJ.
    Supports: on(), once(), off(), emit(), history.
    """

    def __init__(self, history_size: int = 500):
        self._listeners: Dict[str, List[dict]] = defaultdict(list)
        self._history: deque = deque(maxlen=history_size)
        self._stats: Dict[str, int] = defaultdict(int)

    def on(self, event_name: str, handler: Callable, priority: int = 0):
        """Register a persistent listener for an event."""
        self._listeners[event_name].append({
            "handler": handler,
            "once": False,
            "priority": priority,
        })
        # Sort by priority (higher first)
        self._listeners[event_name].sort(key=lambda x: -x["priority"])

    def once(self, event_name: str, handler: Callable, priority: int = 0):
        """Register a one-time listener (auto-removed after first call)."""
        self._listeners[event_name].append({
            "handler": handler,
            "once": True,
            "priority": priority,
        })
        self._listeners[event_name].sort(key=lambda x: -x["priority"])

    def off(self, event_name: str, handler: Callable):
        """Remove a specific handler."""
        if event_name in self._listeners:
            self._listeners[event_name] = [
                l for l in self._listeners[event_name] if l["handler"] != handler
            ]

    def emit(self, event_name: str, source: str = "system", data: Any = None) -> Event:
        """Emit an event synchronously."""
        event = Event(event_name, source, data)
        self._history.append(event.to_dict())
        self._stats[event_name] += 1

        to_remove = []
        for entry in list(self._listeners.get(event_name, [])):
            try:
                result = entry["handler"](event)
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)
                    except RuntimeError:
                        pass
            except Exception as e:
                logger.error(f"Event handler error on '{event_name}': {e}")
            if entry["once"]:
                to_remove.append(entry)

        # Also fire wildcard listeners
        for entry in list(self._listeners.get("*", [])):
            try:
                result = entry["handler"](event)
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)
                    except RuntimeError:
                        pass
            except Exception as e:
                logger.error(f"Wildcard handler error: {e}")
            if entry["once"]:
                to_remove.append(entry)

        # Clean up once-listeners
        for entry in to_remove:
            for name in self._listeners:
                if entry in self._listeners[name]:
                    self._listeners[name].remove(entry)

        return event

    async def emit_async(self, event_name: str, source: str = "system", data: Any = None) -> Event:
        """Emit an event, awaiting async handlers."""
        event = Event(event_name, source, data)
        self._history.append(event.to_dict())
        self._stats[event_name] += 1

        to_remove = []
        for entry in list(self._listeners.get(event_name, [])) + list(self._listeners.get("*", [])):
            try:
                result = entry["handler"](event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Async event handler error on '{event_name}': {e}")
            if entry["once"]:
                to_remove.append(entry)

        for entry in to_remove:
            for name in self._listeners:
                if entry in self._listeners[name]:
                    self._listeners[name].remove(entry)

        return event

    def get_history(self, event_name: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Get event history, optionally filtered."""
        events = list(self._history)
        if event_name:
            events = [e for e in events if e["name"] == event_name or e["name"].startswith(f"{event_name}.")]
        return events[-limit:]

    def get_stats(self) -> dict:
        """Get event counts."""
        return {
            "total": sum(self._stats.values()),
            "events": dict(self._stats),
            "listener_count": {n: len(l) for n, l in self._listeners.items() if l},
        }

    def list_events(self) -> List[str]:
        """List all known event types."""
        known = set(EVENTS.keys())
        known.update(self._stats.keys())
        return sorted(known)


# Singleton
event_system = EventSystem()
