"""
In-memory storage for image data using a session-based dictionary cache.
"""
import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

class InMemoryStorage:
    """A session-based, thread-safe in-memory cache for storing image data."""

    def __init__(self):
        self._caches: Dict[str, Dict[str, np.ndarray]] = {}
        logger.info("Session-based in-memory storage initialized.")

    def _get_or_create_user_cache(self, session_id: str) -> Dict[str, np.ndarray]:
        """Gets or creates a cache for a specific user session."""
        if session_id not in self._caches:
            self._caches[session_id] = {}
            logger.info(f"Created new in-memory cache for session: {session_id}")
        return self._caches[session_id]

    def put(self, session_id: str, key: str, image: np.ndarray) -> None:
        """Stores an image in the cache for a given session."""
        if not isinstance(image, np.ndarray):
            raise TypeError("Only numpy arrays can be stored in InMemoryStorage.")
        
        user_cache = self._get_or_create_user_cache(session_id)
        user_cache[key] = image
        logger.info(f"Stored image with key: {key} for session: {session_id}")

    def get(self, session_id: str, key: str) -> Optional[np.ndarray]:
        """Retrieves an image from the cache for a given session."""
        user_cache = self._get_or_create_user_cache(session_id)
        image = user_cache.get(key)
        if image is not None:
            logger.info(f"Retrieved image with key: {key} for session: {session_id}")
        else:
            logger.warning(f"Image not found for key: {key} in session: {session_id}")
        return image

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
