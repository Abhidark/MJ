"""
Message Bus — Pub/Sub messaging system for inter-module communication.
Modules can publish messages to topics and subscribe to receive them.
Supports sync and async handlers, message history, and wildcard subscriptions.
"""

import time
import logging
import asyncio
from collections import defaultdict, deque
from typing import Callable, Optional, Dict, Any, List

logger = logging.getLogger("mj.message_bus")


class Message:
    """A message sent through the bus."""
    __slots__ = ("topic", "sender", "data", "timestamp", "msg_id")
    _counter = 0

    def __init__(self, topic: str, sender: str, data: Any = None):
        Message._counter += 1
        self.msg_id = Message._counter
        self.topic = topic
        self.sender = sender
        self.data = data
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.msg_id,
            "topic": self.topic,
            "sender": self.sender,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class MessageBus:
    """
    Central message bus for MJ modules.
    Topics use dot notation: "module.action" (e.g., "athena.search_complete").
    Subscribe to "module.*" to get all messages from a module.
    """

    def __init__(self, history_size: int = 200):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: deque = deque(maxlen=history_size)
        self._stats: Dict[str, int] = defaultdict(int)

    def subscribe(self, topic: str, handler: Callable):
        """Subscribe a handler to a topic. Supports wildcards: 'module.*'"""
        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to '{topic}': {handler.__name__}")

    def unsubscribe(self, topic: str, handler: Callable):
        """Remove a handler from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [h for h in self._subscribers[topic] if h != handler]

    def publish(self, topic: str, sender: str, data: Any = None) -> Message:
        """Publish a message to a topic. Returns the Message object."""
        msg = Message(topic, sender, data)
        self._history.append(msg.to_dict())
        self._stats[topic] += 1

        # Collect matching handlers
        handlers = list(self._subscribers.get(topic, []))

        # Wildcard: "module.*" matches "module.anything"
        parts = topic.split(".")
        if len(parts) > 1:
            wildcard = f"{parts[0]}.*"
            handlers.extend(self._subscribers.get(wildcard, []))

        # Global wildcard
        handlers.extend(self._subscribers.get("*", []))

        for handler in handlers:
            try:
                result = handler(msg)
                # If handler is async, schedule it
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)
                    except RuntimeError:
                        pass  # No event loop running
            except Exception as e:
                logger.error(f"Handler error on '{topic}': {e}")

        return msg

    async def publish_async(self, topic: str, sender: str, data: Any = None) -> Message:
        """Async publish — awaits async handlers."""
        msg = Message(topic, sender, data)
        self._history.append(msg.to_dict())
        self._stats[topic] += 1

        handlers = list(self._subscribers.get(topic, []))
        parts = topic.split(".")
        if len(parts) > 1:
            wildcard = f"{parts[0]}.*"
            handlers.extend(self._subscribers.get(wildcard, []))
        handlers.extend(self._subscribers.get("*", []))

        for handler in handlers:
            try:
                result = handler(msg)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Async handler error on '{topic}': {e}")

        return msg

    def get_history(self, topic: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Get message history, optionally filtered by topic."""
        msgs = list(self._history)
        if topic:
            msgs = [m for m in msgs if m["topic"] == topic or m["topic"].startswith(f"{topic}.")]
        return msgs[-limit:]

    def get_stats(self) -> dict:
        """Get message count per topic."""
        return {
            "total": sum(self._stats.values()),
            "topics": dict(self._stats),
            "subscriber_count": {t: len(h) for t, h in self._subscribers.items() if h},
        }

    def clear_history(self):
        """Clear message history."""
        self._history.clear()

    def list_topics(self) -> List[str]:
        """List all topics that have been published to."""
        return list(self._stats.keys())


# Singleton instance
message_bus = MessageBus()
