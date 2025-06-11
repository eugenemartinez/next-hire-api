print("DEBUG: server/core/limiter.py is being loaded") # Add this for debugging

import os
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging
from .config import settings

logger = logging.getLogger(__name__)

is_testing = os.environ.get("TESTING", "").lower() == "true"
if is_testing:
    logger.info("TESTING mode detected - rate limiting will be disabled")

# Only use Redis if REDIS_URL is set and not localhost
redis_url = settings.REDIS_URL
if not redis_url or "localhost" in redis_url or "127.0.0.1" in redis_url:
    logger.warning(f"Rate limiter will use in-memory storage (REDIS_URL='{redis_url}')")
    redis_url = None
else:
    logger.info(f"Rate limiter will attempt to use Redis storage at: {redis_url}")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=redis_url,
    strategy="fixed-window",
    enabled=not is_testing
)