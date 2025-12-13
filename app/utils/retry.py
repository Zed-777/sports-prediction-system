"""
Retry utility with exponential backoff
"""

import asyncio
import logging
import random
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def retry_with_backoff(max_attempts: int = 3, backoff_strategy: str = 'exponential',
                      base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for retrying functions with backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_strategy: 'exponential' or 'linear'
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to delay
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise e

                    # Calculate delay
                    if backoff_strategy == 'exponential':
                        delay = min(base_delay * (2 ** attempt), max_delay)
                    else:  # linear
                        delay = min(base_delay * (attempt + 1), max_delay)

                    # Add jitter
                    if jitter:
                        delay += random.uniform(0, delay * 0.1)

                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError("All retry attempts failed without capturing exception")

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # For synchronous functions, run the async wrapper
            return asyncio.run(async_wrapper(*args, **kwargs))

        # Return async wrapper if function is async, sync wrapper otherwise
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
