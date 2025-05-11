from sqlalchemy.orm import Session # Ensure this is imported
from sqlalchemy import desc, asc, or_, func, and_
from typing import List, Optional, Tuple, Any
import uuid
import bleach # Import bleach
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import text

import models
import schemas
from utils import generate_modification_code, generate_unique_poster_username
# --- Add imports for custom exceptions ---
from core.exceptions import NotFoundError, ForbiddenError

# --- HTML Sanitation Settings (using Bleach) ---
# Based on common rich text editor outputs and job description needs
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'del',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', # ADDED h1, h5, h6
    'ul', 'ol', 'li',
    'a',
    'pre', 'code',
    'blockquote',
    'hr'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'], # Consider forcing target='_blank' later if needed
    # 'pre': ['class'], # Example: if your RTE adds syntax highlighting classes
    # 'code': ['class'], # Example: if your RTE adds syntax highlighting classes
    '*': ['class'] # Allow class attribute on any allowed tag if needed for general styling from RTE
}

# Function to ensure all links open in a new tab
def force_target_blank(name, value):
    if name == 'href':
        return True # Keep the href attribute
    if name == 'target' and value == '_blank':
        return True # Keep target if it's already _blank
    return False # Discard other attributes for <a> or other target values

# More refined attributes for <a> tags to ensure target="_blank"
# This is a bit more advanced; for simplicity, we can start with the basic ALLOWED_ATTRIBUTES
# and refine if needed. For now, the basic ALLOWED_ATTRIBUTES is fine.
# If you want to enforce target="_blank" for all <a> tags:
# You would typically do this by post-processing the attributes or using a custom filter
# with Bleach if it supports attribute value manipulation directly, or by modifying
# the HTML string after bleaching if Bleach's attribute filtering isn't sufficient.
# For now, we'll stick to allowing 'target' and assume frontend/RTE handles setting it to '_blank'.

# === Job CRUD Operations ===

def create_job(db: Session, job: schemas.JobCreate) -> models.Job:
    """
    Create a new job posting.
    Generates a poster_username if not provided and a modification_code.
    Sanitizes the description HTML.
    """
    # Generate a unique poster_username if not provided by the user
    db_poster_username = job.poster_username
    if not db_poster_username:
        db_poster_username = generate_unique_poster_username(db)

    # Generate a unique modification code
    db_modification_code = generate_modification_code(db)

    # Sanitize HTML in description
    sanitized_description = bleach.clean(
        job.description,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True  # Remove disallowed tags instead of escaping them
    )

    db_job = models.Job(
        title=job.title,
        company_name=job.company_name,
        location=job.location,
        description=sanitized_description, # Use sanitized description
        application_info=str(job.application_info),
        job_type=job.job_type,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        poster_username=db_poster_username,
        tags=job.tags,
        modification_code=db_modification_code
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job(db: Session, job_id: uuid.UUID) -> models.Job: # Changed return type
    """
    Retrieve a single job by its ID.
    Raises NotFoundError if the job does not exist.
    """
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise NotFoundError(detail=f"Job with ID {job_id} not found.")
    return db_job

def get_jobs_by_ids(db: Session, job_ids: List[uuid.UUID]) -> List[models.Job]:
    """
    Retrieves a list of job postings by their UUIDs.
    """
    if not job_ids:
        return []
    # Ensure that the elements in job_ids are actual UUID objects if they are coming in as strings
    # However, schemas.JobIdsList should already validate them as UUID4.
    return db.query(models.Job).filter(models.Job.id.in_(job_ids)).all()

def verify_modification_code(db: Session, job_id: uuid.UUID, modification_code: str) -> bool: # Changed return type to bool
    """
    Verifies if the provided modification_code matches the one stored for the given job_id.
    Raises NotFoundError if the job does not exist.
    Returns True if the code is correct, False otherwise.
    """
    db_job_code_tuple = db.query(models.Job.modification_code).filter(models.Job.id == job_id).first()
    
    if not db_job_code_tuple:
        raise NotFoundError(detail=f"Job with ID {job_id} not found for verification.")
        
    return db_job_code_tuple.modification_code == modification_code # Return boolean

def get_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at", # e.g., "created_at", "title"
    sort_order: Optional[str] = "desc" # "asc" or "desc"
) -> List[models.Job]:
    """
    Retrieve a list of jobs with pagination, search, and sorting.
    """
    query = db.query(models.Job)

    # Search functionality (basic example across title, company, description, tags)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.Job.title.ilike(search_term),
                models.Job.company_name.ilike(search_term),
                models.Job.description.ilike(search_term),
                # models.Job.location.ilike(search_term), # Add if desired
                # models.Job.tags.any(search_term) # For searching within ARRAY, might need specific PG syntax or cast
            )
        )
        # A more robust tag search might involve checking if the search term is IN tags array.
        # For example, using `models.Job.tags.any(search, operator=postgresql.Comparator.ilike)`
        # or `models.Job.tags.contains([search_term_for_tag])` if search is for a whole tag.

    # Sorting
    if sort_by and hasattr(models.Job, sort_by):
        column_to_sort = getattr(models.Job, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(column_to_sort))
        else:
            query = query.order_by(column_to_sort.asc())
    else:
        # Default sort
        query = query.order_by(desc(models.Job.created_at))


    return query.offset(skip).limit(limit).all()

def update_job(
    db: Session,
    job_id: uuid.UUID,
    job_update: schemas.JobUpdate,
    modification_code: str
) -> models.Job: # Changed return type
    """
    Update an existing job. Requires the correct modification_code.
    Sanitizes the description HTML if provided.
    Raises NotFoundError if the job does not exist.
    Raises ForbiddenError if the modification code is incorrect.
    """
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise NotFoundError(detail=f"Job with ID {job_id} not found for update.")
    
    if db_job.modification_code != modification_code:
        raise ForbiddenError(detail="Incorrect modification code for update.")

    update_data = job_update.model_dump(exclude_unset=True)

    # Sanitize HTML in description if it's being updated
    if 'description' in update_data and update_data['description'] is not None:
        update_data['description'] = bleach.clean(
            update_data['description'],
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )

    for key, value in update_data.items():
        setattr(db_job, key, value)

    db.add(db_job) # or db.merge(db_job) if that's preferred, add is fine for tracked objects
    db.commit()
    db.refresh(db_job)
    return db_job

def delete_job(db: Session, job_id: uuid.UUID, modification_code: str) -> models.Job: # Changed return type
    """
    Delete a job. Requires the correct modification_code.
    Returns the deleted job object if successful.
    Raises NotFoundError if the job does not exist.
    Raises ForbiddenError if the modification code is incorrect.
    """
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise NotFoundError(detail=f"Job with ID {job_id} not found for deletion.")

    if db_job.modification_code != modification_code:
        raise ForbiddenError(detail="Incorrect modification code for deletion.")

    # Store a reference or key details if needed after deletion, as db_job will be expired
    # For returning the object, it's fine as is, but accessing its attributes after commit might be an issue
    # if not handled carefully or if the session is closed.
    # However, for the purpose of returning it as per the current signature, this is okay.
    # The object's state reflects its last known state before deletion.
    
    db.delete(db_job)
    db.commit()
    return db_job # Return the object that was deleted

def get_jobs_and_total(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    tags_query: Optional[List[str]] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    job_type_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    company_name_filter: Optional[str] = None
) -> Tuple[List[models.Job], int]:
    """
    Retrieves a paginated list of jobs based on various filter and sort criteria,
    along with the total count of jobs matching the criteria.
    """
    query = db.query(models.Job)

    # Apply filters
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(models.Job.title).ilike(search_term),
                func.lower(models.Job.company_name).ilike(search_term),
                func.lower(models.Job.description).ilike(search_term)
            )
        )

    if tags_query:
        # Filter for jobs that contain ALL specified tags in their 'tags' array
        # This requires the tags in the database and query to be consistently cased (e.g., lowercase)
        # If tags in DB are mixed case, ensure they are queried appropriately or normalized at insertion.
        # For PostgreSQL, using ARRAY Überschneidung (&&) or Enthaltensein (@>)
        # Assuming tags_query contains lowercase tags and DB tags are also stored/queried as lowercase.
        # The @> operator checks if the left array contains the right array.
        # We need to check if the job's tags array contains each of the query tags.
        # A simpler approach for "any of these tags" is .contains() if tags were a simple string.
        # For array containment of multiple items (AND logic), it's more complex.
        # Let's assume for now tags are stored normalized (e.g., lowercase).
        # And we want jobs that have AT LEAST ONE of the tags (OR logic for tags)
        # If AND logic is needed (job must have ALL tags), the query is different.
        # PRD: "filter by tags (comma-separated list)" - implies OR logic usually.
        
        # For OR logic (job has any of the tags):
        # This uses the `&&` (overlaps) operator for array types in PostgreSQL.
        # Ensure tags_query is a list of strings.
        if tags_query: # Ensure it's not an empty list if no tags were passed
            query = query.filter(models.Job.tags.op('&&')(tags_query)) # type: ignore

    if job_type_filter:
        query = query.filter(models.Job.job_type == job_type_filter)
    
    if location_filter:
        # Using ilike for case-insensitive exact match for location
        query = query.filter(func.lower(models.Job.location) == location_filter.lower())

    if company_name_filter:
        # Using ilike for case-insensitive exact match for company name
        query = query.filter(func.lower(models.Job.company_name) == company_name_filter.lower())

    # Get total count before applying pagination and sorting for count
    total_jobs = query.count()

    # Apply sorting with case-insensitivity for title
    if sort_by == "title":
        # Use func.lower for case-insensitive title sorting
        if sort_order == "asc":
            query = query.order_by(asc(func.lower(models.Job.title)))
        else:
            query = query.order_by(desc(func.lower(models.Job.title)))
    else:
        # For other columns, use regular sorting
        sort_column = getattr(models.Job, sort_by, models.Job.created_at)  # Default to created_at
        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

    # Apply pagination
    jobs = query.offset(skip).limit(limit).all()
    
    return jobs, total_jobs

# === Tag CRUD Operations (or utility functions) ===

def get_unique_tags(db: Session) -> List[str]:
    """
    Retrieves a list of all unique tags used across all jobs.
    Tags are stored in an ARRAY column in the Job model.
    This function unnests the tags and returns a distinct list.
    """
    # Using SQLAlchemy's text() for a query that might be more straightforward with raw SQL
    # for unnesting and distinct operations on array elements.
    # Alternatively, one could query all job.tags, then process in Python,
    # but that's less efficient for the database.
    
    # The query `SELECT DISTINCT unnest(tags) FROM jobs WHERE tags IS NOT NULL AND cardinality(tags) > 0;`
    # is what we want to achieve.
    # `func.unnest` can be used with SQLAlchemy.
    
    # Query to select distinct tags by unnesting the 'tags' array column
    # and filtering out NULL or empty arrays to prevent errors with unnest.
    query = (
        db.query(func.unnest(models.Job.tags).label("tag"))
        .filter(models.Job.tags.isnot(None)) # Ensure tags array is not null
        .filter(func.cardinality(models.Job.tags) > 0) # Ensure tags array is not empty
        .distinct()
    )
    
    # The result will be a list of Row objects, each with a single 'tag' attribute.
    # We need to extract these tag strings into a simple list.
    unique_tags_rows = query.all()
    unique_tags_list = [row.tag for row in unique_tags_rows if row.tag is not None] # Ensure tag itself is not null after unnest
    
    return unique_tags_list

# We will also need utility functions for generating unique poster_username and modification_code.
# These will likely involve checking the database for uniqueness.
# Let's plan to create a `server/utils.py` for these.