import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, urlunparse # Ensure this import is present

from main import app # Your FastAPI app
from core.database import Base, get_db # Import your Base and get_db
from core.config import settings

# Set testing mode for rate limiter
os.environ["TESTING"] = "true"

# --- Test Database Setup ---
# Get the main database URL string
db_url_str = settings.DATABASE_URL.get_secret_value() # Use .get_secret_value()

# Parse the URL
parsed_url = urlparse(db_url_str)

# Extract the original database name from the path component
original_db_name_from_path = parsed_url.path.lstrip('/')

# Construct the test database name
test_db_name = f"{original_db_name_from_path}_test"

# Create the new path for the test database URL
test_db_path = f"/{test_db_name}"

# Reconstruct the URL tuple with the new database path
url_parts = list(parsed_url)
url_parts[2] = test_db_path # Index 2 is the 'path' component

ACTUAL_TEST_DATABASE_URL = urlunparse(url_parts)
print(f"--- Using Test Database URL: {ACTUAL_TEST_DATABASE_URL} ---") # For verification

engine = create_engine(
    ACTUAL_TEST_DATABASE_URL
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Fixture to create tables for each test session ---
@pytest.fixture(scope="session") # Changed to session scope for efficiency
def db_engine():
    Base.metadata.create_all(bind=engine) # Create tables
    yield engine # Provide the engine in case it's needed
    Base.metadata.drop_all(bind=engine) # Drop tables after all tests in session

# --- Fixture for database session, overridden for tests ---
@pytest.fixture()
def db_session(db_engine): # Depend on db_engine to ensure tables are created
    connection = db_engine.connect()
    # begin a non-ORM transaction
    transaction = connection.begin()
    # bind an ORM session to the connection
    db = TestingSessionLocal(bind=connection)

    yield db

    db.close()
    # rollback - everything that happened with the
    # session above (including calls to commit)
    # is rolled back.
    transaction.rollback()
    connection.close()

# --- Override get_db dependency ---
def override_get_db(db_session_fixture): # A wrapper to pass the fixture
    def get_db_override():
        yield db_session_fixture
    return get_db_override

# --- Test Client Fixture ---
@pytest.fixture()
def client(db_session): # client depends on db_session
    # Override the get_db dependency for the app
    app.dependency_overrides[get_db] = lambda: db_session
    
    with TestClient(app) as c:
        yield c
    
    # Clean up overrides after test
    app.dependency_overrides.clear()

# --- Optional: Fixture to clear limiter for each test ---
# from core.limiter import limiter
# @pytest.fixture(autouse=True)
# def reset_limiter_storage():
#     """Resets the limiter storage before each test to ensure independence."""
#     if hasattr(limiter, 'reset'): 
#         limiter.reset()
#     elif hasattr(limiter, '_storage') and hasattr(limiter._storage, 'flushdb'): 
#         limiter._storage.flushdb()
#     elif hasattr(limiter, '_storage') and hasattr(limiter._storage, 'clear'): 
#         limiter._storage.clear()
#     yield

@pytest.fixture
def sample_job_payload_factory():
    def _factory(**kwargs):
        payload = {
            "title": "Software Engineer",
            "company_name": "Tech Solutions Inc.",
            "location": "San Francisco, CA",
            "description": "Developing next-gen software.",
            "application_info": "apply@techsolutions.dev",
            "job_type": "full-time",
            "salary_min": 80000,
            "salary_max": 120000,
            "salary_currency": "USD",
            "poster_username": "test_user",
            "tags": ["python", "fastapi", "developer"]
        }
        payload.update(kwargs)
        return payload
    return _factory