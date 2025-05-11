import time
import uuid # For generating unique request IDs
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from .logging_config import get_logger # Import our get_logger function

# It's good practice to get a logger specific to the middleware
logger = get_logger("api.middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Bind request_id to contextvars for structlog if you want it in all subsequent logs for this request
        # This requires structlog.contextvars to be part of your processor chain,
        # or you can explicitly pass it. For now, we'll log it directly here.
        # structlog.contextvars.bind_contextvars(request_id=request_id)


        start_time = time.time()

        # Log basic request info before processing
        # We can bind some initial info to the logger for this request
        req_logger = logger.bind(
            request_id=request_id,
            http_method=request.method,
            http_path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
            # http_user_agent=request.headers.get("user-agent", "unknown") # Optional
        )
        req_logger.info("request_started")

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000  # in milliseconds
            status_code = response.status_code

        except Exception as e:
            # If an unhandled exception occurs, log it and re-raise
            # FastAPI's exception handlers will then convert it to a 500 response
            process_time = (time.time() - start_time) * 1000
            status_code = 500 # Default for unhandled exceptions
            req_logger.error(
                "request_exception",
                status_code=status_code,
                process_time_ms=round(process_time, 2),
                exception=str(e),
                # Consider adding exc_info=True if you want the full traceback in the log
                # exc_info=True, # This will be picked up by structlog.processors.format_exc_info
            )
            raise # Re-raise the exception to be handled by FastAPI's error handlers
        else:
            # Log completion info
            req_logger.info(
                "request_finished",
                status_code=status_code,
                process_time_ms=round(process_time, 2)
            )
        
        # Add request_id to response headers (optional, but good for client-side debugging)
        response.headers["X-Request-ID"] = request_id
        # structlog.contextvars.clear_contextvars() # Clear contextvars after request
        return response
