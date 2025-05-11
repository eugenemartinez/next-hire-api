import logging
import sys
import structlog
from structlog.types import Processor # For type hinting if desired

from .config import settings

def setup_logging():
    """
    Configures comprehensive, unified Structlog logging for the application.
    - Human-readable, colored logs in DEBUG_MODE.
    - JSON logs in production.
    - Processes logs from both structlog and standard library (e.g., Uvicorn).
    """

    # Determine log level based on DEBUG_MODE
    log_level = logging.DEBUG if settings.DEBUG_MODE else logging.INFO

    # Shared processors for all logs (structlog's own and foreign)
    # These run BEFORE the final rendering.
    shared_processors: list[Processor] = [
        structlog.stdlib.add_logger_name,  # Adds logger name (e.g., "main", "uvicorn.error")
        structlog.stdlib.add_log_level,    # Adds log level (e.g., "info", "error")
        structlog.stdlib.PositionalArgumentsFormatter(), # Formats %s style messages
        structlog.processors.StackInfoRenderer(),  # Renders stack info for standard library
        structlog.dev.set_exc_info,         # Adds exc_info to event_dict if present (for structlog loggers)
        structlog.processors.format_exc_info, # Formats exception info from exc_info
        structlog.processors.TimeStamper(fmt="iso", utc=True), # ISO8601 timestamp
        # Optional: Add module, function, line number
        # structlog.processors.CallsiteParameterAdder(
        #     [
        #         structlog.processors.CallsiteParameter.MODULE,
        #         structlog.processors.CallsiteParameter.FUNC_NAME,
        #         structlog.processors.CallsiteParameter.LINENO,
        #     ]
        # ),
    ]

    # Configure structlog for logs made via structlog.get_logger()
    structlog.configure(
        processors=shared_processors + [
            # This processor prepares the event_dict for the stdlib formatter instance
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Determine the final renderer based on DEBUG_MODE
    if settings.DEBUG_MODE:
        final_renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        final_renderer = structlog.processors.JSONRenderer()

    # Configure the standard library root logger and its handler
    # This is the key to unified logging.
    formatter = structlog.stdlib.ProcessorFormatter(
        # The 'processor' here is the final structlog renderer (JSON or Console).
        # It will render the event_dict AFTER foreign_pre_chain (for foreign logs)
        # or after structlog's own processors (for structlog logs).
        processor=final_renderer,
        # 'foreign_pre_chain' processes logs from non-structlog loggers (e.g., uvicorn)
        # using our shared_processors before they hit the final_renderer.
        foreign_pre_chain=shared_processors.copy(), # Use a copy to avoid modification issues if any
    )

    # Create a handler that writes to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter) # Set our Structlog-aware formatter

    # Get the root logger
    root_logger = logging.getLogger()

    # Remove any existing handlers to prevent duplicate logs if setup_logging is called multiple times
    # (though it should ideally be called only once at application startup).
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level) # Set the root logger level

    # Optionally, adjust log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if not settings.DEBUG_MODE else logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.DEBUG_MODE else logging.INFO)


    # Log a confirmation message using the configured logger
    logger = get_logger(__name__) # Use our helper
    logger.info(
        "Unified Structlog logging configured", 
        mode="DEBUG (Console)" if settings.DEBUG_MODE else "PRODUCTION (JSON)",
        effective_log_level=logging.getLevelName(root_logger.getEffectiveLevel())
    )

def get_logger(name: str):
    """
    Returns a Structlog-bound logger.
    """
    return structlog.get_logger(name)

# Example of how to get a logger at the module level if needed immediately
# module_logger = get_logger(__name__)