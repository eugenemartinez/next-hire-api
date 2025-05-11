from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError, DBAPIError
from core.config import settings # Import your settings
import logging

logger = logging.getLogger(__name__)

# Use .get_secret_value() to retrieve the actual string from SecretStr
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.get_secret_value()

# Create SQLAlchemy engine
# pool_pre_ping=True helps detect and refresh stale connections
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# Create a SessionLocal class to generate database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
# All our database models will inherit from this class
Base = declarative_base()

# Dependency to get a DB session
# This will be used in path operation functions to get a database session.
# It ensures the session is always closed after the request, even if there are exceptions.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to check database connection (already defined, kept for health checks)
def check_db_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "Database connection successful."
    except OperationalError as e:
        logger.error(f"Database OperationalError: {e}")
        return False, f"Database connection failed (OperationalError): {e.args[0] if e.args else 'Unknown error'}"
    except DBAPIError as e:
        logger.error(f"Database DBAPIError: {e}")
        return False, f"Database connection failed (DBAPIError): {e.args[0] if e.args else 'Unknown error'}"
    except Exception as e:
        logger.error(f"Unexpected database connection error: {e}", exc_info=True)
        return False, f"Database connection failed with an unexpected error: {str(e)}"

# We might add a function here later to create all tables defined by Base's metadata
# e.g., def create_db_tables(): Base.metadata.create_all(bind=engine)
# However, for Neon, we'll use manual SQL scripts, so this might only be for local dev if we choose.