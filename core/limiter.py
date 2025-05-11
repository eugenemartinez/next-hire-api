print("DEBUG: server/core/limiter.py is being loaded") # Add this for debugging

from slowapi import Limiter
from slowapi.util import get_remote_address
import logging  # Import the logging module

from .config import settings

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# Log the REDIS_URL being used for the limiter
if settings.REDIS_URL and ("redis://" in settings.REDIS_URL or "rediss://" in settings.REDIS_URL):
    logger.info(f"Rate limiter will attempt to use Redis storage at: {settings.REDIS_URL}")
else:
    # This case would now only happen if REDIS_URL is empty or doesn't look like a Redis URL at all
    logger.warning(f"Rate limiter REDIS_URL does not appear to be a valid Redis connection string: '{settings.REDIS_URL}'. Defaulting to in-memory storage if storage_uri is None or invalid.")

# Initialize the limiter instance
limiter = Limiter(
    key_func=get_remote_address,  # Standard key function
    storage_uri=settings.REDIS_URL,  # slowapi will use in-memory if this is None or invalid for Redis
    strategy="fixed-window"
    # default_limits=["100/minute"] # Example: if you want a global default
)

# You might also want to configure basic logging in your main.py if you haven't already,
# so that these log messages appear in your console.
# For example, in main.py:
# import logging
# logging.basicConfig(level=logging.INFO)