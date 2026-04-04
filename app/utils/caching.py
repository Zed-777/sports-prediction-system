"""Caching utilities
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CacheManager:
    """Simple disk-based cache manager"""

    def __init__(self, config: dict[str, Any]):
        self.enabled = config.get("enabled", True)
        self.ttl_seconds = config.get("ttl_seconds", 3600)
        self.store_type = config.get("store", "disk")

        # Set up cache directory
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def get(self, key: str) -> Any | None:
        """Get item from cache"""
        if not self.enabled:
            return None

        try:
            cache_file = self._get_cache_file(key)

            if not cache_file.exists():
                return None

            # Check if cache is expired
            file_age = datetime.now() - datetime.fromtimestamp(
                cache_file.stat().st_mtime,
            )
            if file_age.total_seconds() > self.ttl_seconds:
                cache_file.unlink()  # Remove expired cache
                return None

            # Load cached data
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)

            logger.debug(f"Cache hit for key: {key}")
            return data

        except Exception as e:
            logger.warning(f"Error reading from cache: {e}")
            return None

    async def set(self, key: str, value: Any) -> bool:
        """Set item in cache"""
        if not self.enabled:
            return False

        try:
            cache_file = self._get_cache_file(key)

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(value, f, default=str)

            logger.debug(f"Cache set for key: {key}")
            return True

        except Exception as e:
            logger.warning(f"Error writing to cache: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete item from cache"""
        try:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
                return True
            return False
        except Exception as e:
            logger.warning(f"Error deleting from cache: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cache"""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            return True
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
            return False

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key"""
        # Hash the key to create a safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
