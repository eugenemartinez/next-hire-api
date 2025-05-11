# Remove the old standard logging import if it's only used for basicConfig
# import logging # This can be removed if not used for anything else now

# --- Import Structlog logging configuration ---
from core.logging_config import setup_logging, get_logger

# --- Call setup_logging() as early as possible ---
setup_logging() # THIS IS THE NEW SETUP CALL

# --- Get a logger for the main module ---
logger = get_logger(__name__) # Use this logger for main.py specific logs

# --- Imports for FastAPI and other modules ---
from fastapi import FastAPI, Depends, Request, status # Ensure status is imported if you use it in the handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder # <<<< MAKE SURE THIS IS IMPORTED
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import asynccontextmanager # ADD THIS IMPORT
from fastapi.staticfiles import StaticFiles # ADD THIS IMPORT FOR STATIC FILES

# Import routers
from routers import jobs as jobs_router
from routers import tags as tags_router
from core.config import settings
from core.database import get_db, engine # Assuming get_db and engine are correctly set up
from core.middleware import RequestLoggingMiddleware

# --- Import Custom Exceptions ---
from core.exceptions import AppException # Import your base custom exception
from starlette.exceptions import HTTPException as StarletteHTTPException # Add this import

# --- Add these imports for slowapi ---
from slowapi.errors import RateLimitExceeded
from core.limiter import limiter # Assuming your limiter setup

# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI): # Renamed app to app_instance to avoid conflict with global 'app'
    # Code to run on startup
    logger.info("application_startup_initiated")
    logger.info("debug_mode_status", status="ON" if settings.DEBUG_MODE else "OFF")
    logger.info("allowed_cors_origins", origins=settings.cors_origins_list if settings.CORS_ALLOWED_ORIGINS else ["http://localhost:3000", "http://127.0.0.1:3000"])
    
    db_url_preview = settings.DATABASE_URL.get_secret_value()
    if len(db_url_preview) > 50: # Adjusted preview length for potentially longer URLs
        db_url_preview = db_url_preview[:20] + "..." + db_url_preview[-20:]
    logger.info("database_url_configured", database_url_preview=db_url_preview)
    logger.info("rate_limiter_redis_url", redis_url=settings.REDIS_URL)
    
    try:
        # Use a synchronous context manager for the engine connection test
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.scalar_one() == 1:
                logger.info("database_connection_successful")
            else:
                logger.error("database_connection_test_failed", reason="unexpected_query_result")
    except Exception as e:
        logger.error("database_connection_failed_startup", error=str(e), exc_info=True)
    
    logger.info("application_startup_complete")
    yield
    # Code to run on shutdown (if any)
    logger.info("application_shutdown_initiated")
    # Perform any cleanup here
    logger.info("application_shutdown_complete")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    ## NextHire Job Board API
    
    This API provides endpoints for managing job postings, retrieving job details, and other utility functions.
    
    ### Features
    
    * Create, update, and delete job postings
    * Search and filter jobs by various criteria
    * Batch retrieve job details
    * Manage tags
    * Rate limiting for security
    
    ### Authentication
    
    Job modification operations require a modification code provided at job creation.
    """,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    swagger_ui_parameters={"syntaxHighlight.theme": "monokai"}
)

# Add this after the FastAPI app creation but before middleware
# Mount the static directory to serve custom CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add this line to use custom Swagger UI CSS
app.swagger_ui_css = ["/static/custom_swagger.css"]

# Your existing middleware setup
app.add_middleware(RequestLoggingMiddleware)
app.state.limiter = limiter

# --- Custom Exception Handlers ---

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    Handles exceptions that are instances of AppException (and its subclasses).
    Logs the error and returns a JSON response.
    """
    # The RequestLoggingMiddleware should have already logged the request_started
    # and will log request_finished/request_exception.
    # Here, we log the specific application error that occurred.
    # The request_id should be available if bound by the middleware,
    # or we can extract it from request.state if we explicitly put it there.
    # For now, the middleware logs the exception if it's unhandled by a route.
    # If an AppException is caught here, it means it was raised within a route.
    
    # Log the application-specific error
    # The RequestLoggingMiddleware will log the overall request failure.
    # This log provides details about the *specific* business logic error.
    logger.error(
        "application_error_occurred",
        error_type=exc.__class__.__name__,
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown",
        # exc_info=True # Consider if you want full stack trace for all AppExceptions
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic RequestValidationError.
    Logs the validation errors and returns a 422 JSON response.
    """
    logger.warning( 
        "request_validation_error",
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown",
        errors=jsonable_encoder(exc.errors()) # <<<< USE jsonable_encoder HERE for logging
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, # Or just 422
        content=jsonable_encoder({"detail": exc.errors()}), # <<<< USE jsonable_encoder HERE for the response content
    )

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    client_ip = request.client.host if request.client else "unknown_ip"
    logger.warning(
        "rate_limit_exceeded", 
        client_ip=client_ip, 
        path=request.url.path,
        detail=exc.detail
    )
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handles FastAPI's HTTPException (and Starlette's).
    Logs the error and returns a JSON response.
    """
    logger.error(
        "http_exception_occurred",
        error_type=exc.__class__.__name__,
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown",
        # exc_info=True if exc.status_code >= 500 else False # Optional: full trace for 5xx
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handles any other unhandled exceptions.
    Logs the error as critical and returns a generic 500 response.
    """
    logger.critical(
        "unhandled_exception_occurred",
        error_type=exc.__class__.__name__,
        detail=str(exc),
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown",
        exc_info=True, # Always include full stack trace for unexpected errors
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal server error occurred."},
    )

# --- End of Custom Exception Handlers ---

# --- CORS Middleware ---
# This should typically come AFTER the logging middleware if you want to log
# details before CORS might reject a request, though order can vary based on needs.
if settings.CORS_ALLOWED_ORIGINS:
    logger.info("cors_configured", configured_origins=settings.cors_origins_list) # Use the new logger
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"] # Example defaults
    logger.warning("cors_not_configured_using_defaults", using_default_origins=default_origins) # Use the new logger
    app.add_middleware(
        CORSMiddleware,
        allow_origins=default_origins, 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- Include Routers with API Prefix ---
# All routes from jobs_router and tags_router will be prefixed with settings.API_V1_STR (e.g., /api)
app.include_router(jobs_router.router, prefix=settings.API_V1_STR)
app.include_router(tags_router.router, prefix=settings.API_V1_STR)


# --- Root endpoint (remains at '/') ---
@app.get("/", tags=["Root"])
async def root(db: Session = Depends(get_db)):
    """
    Root endpoint for the NextHire API.
    Provides a welcome message and basic API information including DB status.
    """
    db_status = "unknown"
    db_url_type = "unknown"
    db_url_str = settings.DATABASE_URL.get_secret_value()
    if "localhost" in db_url_str or "127.0.0.1" in db_url_str:
        db_url_type = "local"
    elif "neon.tech" in db_url_str: # Example, adjust if you use a different cloud DB
        db_url_type = "cloud (Neon)" 
    # Add other cloud provider checks if necessary
    
    try:
        # A simple query to check DB connectivity
        db.execute(text("SELECT 1")).scalar_one()
        db_status = "connected"
    except Exception:
        db_status = "error (failed to connect or query)"

    # Log this access (optional, but can be useful)
    # logger.debug("root_endpoint_accessed") 

    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!", 
        "documentation_urls": [
            f"{settings.API_V1_STR}/docs",
            f"{settings.API_V1_STR}/redoc"
        ],
        "api_version": app.version,
        "database_status": db_status,
        "database_type": db_url_type,
        "debug_mode": settings.DEBUG_MODE,
        "cors_allowed_origins": settings.cors_origins_list if settings.CORS_ALLOWED_ORIGINS else ["http://localhost:3000", "http://127.0.0.1:3000"]
    }
