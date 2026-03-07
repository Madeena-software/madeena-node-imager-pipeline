"""
In-memory storage for image data using a session-based dictionary cache.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class InMemoryStorage:
    """A session-based, thread-safe in-memory cache for storing session artifacts."""

    def __init__(self):
        self._caches: Dict[str, Dict[str, Any]] = {}
        logger.info("Session-based in-memory storage initialized.")

    def _get_or_create_user_cache(self, session_id: str) -> Dict[str, Any]:
        """Gets or creates a cache for a specific user session."""
        if session_id not in self._caches:
            self._caches[session_id] = {}
            logger.info(f"Created new in-memory cache for session: {session_id}")
        return self._caches[session_id]

    def put(self, session_id: str, key: str, value: Any) -> None:
        """Stores a session-scoped value in the cache."""
        user_cache = self._get_or_create_user_cache(session_id)
        user_cache[key] = value
        logger.info("Stored key %s for session %s", key, session_id)

    def get(self, session_id: str, key: str) -> Optional[Any]:
        """Retrieves a session-scoped value from the cache."""
        user_cache = self._get_or_create_user_cache(session_id)
        value = user_cache.get(key)
        if value is not None:
            logger.info("Retrieved key %s for session %s", key, session_id)
        else:
            logger.warning("Key not found: %s in session %s", key, session_id)
        return value

    def delete(self, session_id: str, key: str) -> bool:
        """Deletes an image from the cache for a given session."""
        if session_id in self._caches and key in self._caches[session_id]:
            del self._caches[session_id][key]
            logger.info(f"Deleted image with key: {key} for session: {session_id}")
            return True
        return False

    def clear_session(self, session_id: str) -> bool:
        """Clears the entire cache for a given session."""
        if session_id in self._caches:
            self._caches[session_id].clear()
            logger.info(f"Cleared in-memory storage for session: {session_id}")
            return True
        return False

    def destroy_session_cache(self, session_id: str) -> bool:
        """Destroys a user's cache, e.g., on logout or session expiry."""
        if session_id in self._caches:
            del self._caches[session_id]
            logger.info(f"Destroyed cache for session: {session_id}")
            return True
        return False


# Singleton instance
storage = InMemoryStorage()
