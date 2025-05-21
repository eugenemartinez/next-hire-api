from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

import crud
import models
import schemas
from core.database import get_db
from core.limiter import limiter
# --- Add imports for custom exceptions ---
from core.exceptions import NotFoundError, ForbiddenError # Keep these if routers raise them directly for other reasons

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)

# === API Endpoints for Jobs ===

@router.post("/", response_model=schemas.JobWithModificationCode, status_code=status.HTTP_201_CREATED)
@limiter.limit("50/day")
async def create_new_job(
    request: Request,
    job: schemas.JobCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new job posting.
    - **title**: Title of the job (max 100 chars)
    - **company_name**: Name of the company (max 100 chars)
    - **description**: Detailed job description
    - **application_info**: Email or URL for application
    - **poster_username** (optional): Username of the poster. If not provided, one will be generated.
    - Other optional fields as defined in JobCreate schema.

    Returns the created job details including its ID, generated modification_code, and timestamps.
    """
    # Note: CRUD operations are typically synchronous.
    # If crud.create_job is synchronous, FastAPI will run it in a thread pool.
    db_job = crud.create_job(db=db, job=job)
    if not db_job:
        # Keeping as HTTPException for 500, as it's a true server error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create job")
    return db_job

@router.get("/", response_model=schemas.JobListResponse)
async def read_jobs_list(
    # ...existing parameters...
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search term for title, company, description."),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by (e.g., 'python,fastapi')."),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by: title, created_at, updated_at, company_name, location."),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc. Default is desc for created_at."),
    job_type: Optional[schemas.JobType] = Query(None, description="Filter by job type."),
    location: Optional[str] = Query(None, min_length=1, max_length=100, description="Filter by exact location string."),
    company_name: Optional[str] = Query(None, min_length=1, max_length=100, description="Filter by exact company name."),
    # Add new query parameters for salary filtering
    salary_min: Optional[int] = Query(None, ge=0, description="Minimum salary to filter by."),
    salary_max: Optional[int] = Query(None, ge=0, description="Maximum salary to filter by."),
    salary_currency: Optional[str] = Query(None, min_length=3, max_length=3, description="Currency code for salary filtering (e.g., 'USD')."),
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of job postings with pagination, search, filtering, and sorting.
    """
    tag_list = [tag.strip() for tag in tags.split(',')] if tags else None
    
    jobs, total_jobs = crud.get_jobs_and_total(
        db, 
        skip=skip, 
        limit=limit, 
        search=search, 
        tags_query=tag_list, 
        sort_by=sort_by, 
        sort_order=sort_order,
        job_type_filter=job_type.value if job_type else None,
        location_filter=location,
        company_name_filter=company_name,
        # Add new salary filter parameters
        salary_min_filter=salary_min,
        salary_max_filter=salary_max,
        salary_currency_filter=salary_currency
    )
    return {"jobs": jobs, "limit": limit, "skip": skip, "total": total_jobs}

@router.get("/{job_id}", response_model=schemas.Job)
async def read_specific_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve a single job posting by its ID.
    """
    # The crud.get_job will now raise NotFoundError if not found.
    return crud.get_job(db, job_id=job_id)

@router.patch("/{job_id}", response_model=schemas.JobWithModificationCode)
@limiter.limit("50/day")
async def update_existing_job(
    request: Request,
    job_id: uuid.UUID,
    job_update: schemas.JobUpdate,
    modification_code: str = Header(..., alias="X-Modification-Code", min_length=8, max_length=8, description="The 8-character modification code for the job."),
    db: Session = Depends(get_db)
):
    """
    Update an existing job posting.
    """
    # crud.update_job will now raise NotFoundError or ForbiddenError.
    return crud.update_job(db=db, job_id=job_id, job_update=job_update, modification_code=modification_code)

@router.delete("/{job_id}", response_model=schemas.JobDeleteResponse)
@limiter.limit("50/day")
async def delete_specific_job(
    request: Request,
    job_id: uuid.UUID,
    modification_code: str = Header(..., alias="X-Modification-Code", min_length=8, max_length=8, description="The 8-character modification code for the job."),
    db: Session = Depends(get_db)
):
    """
    Delete a specific job posting.
    """
    # crud.delete_job will now raise NotFoundError or ForbiddenError.
    deleted_job_object = crud.delete_job(db=db, job_id=job_id, modification_code=modification_code)
    return schemas.JobDeleteResponse(message="Job deleted successfully", job_id=deleted_job_object.id)

@router.get("/{job_id}/related", response_model=List[schemas.Job], tags=["jobs"])
async def get_related_jobs_route(
    job_id: uuid.UUID,
    limit: int = Query(3, ge=1, le=10, description="Number of related jobs to return."), # Default to 3
    db: Session = Depends(get_db)
):
    """
    Get a list of jobs related to the specified job_id based on shared tags.
    """
    # First, get the current job to extract its tags
    # crud.get_job will raise NotFoundError if the job_id is invalid,
    # which will be handled by FastAPI's error handling (resulting in a 404).
    current_job = crud.get_job(db, job_id=job_id) 

    if not current_job.tags:
        return [] # No tags on the current job, so no tag-based related jobs

    related_jobs_list = crud.get_related_jobs(
        db=db,
        current_job_id=current_job.id,
        source_tags=current_job.tags,
        limit=limit
    )
    return related_jobs_list

# --- Auxiliary Job Endpoints ---

@router.post("/saved", response_model=List[schemas.Job], tags=["jobs-utils"]) 
async def get_saved_jobs_details(payload: schemas.JobIdsList, db: Session = Depends(get_db)):
    """
    Batch retrieval of job details by a list of job UUIDs.
    Request Body: `{"job_ids": ["uuid1", "uuid2"]}`
    Returns a list of job objects. If an ID is not found, it's omitted from the list.
    """
    if not payload.job_ids:
        # Consider if an empty list for empty input is a "bad request" or just an empty valid result.
        # If it should be an error for empty job_ids:
        # raise BadRequestError(detail="job_ids list cannot be empty.")
        return [] # Current behavior
    jobs = crud.get_jobs_by_ids(db=db, job_ids=payload.job_ids)
    return jobs

@router.post("/{job_id}/verify", response_model=schemas.JobVerificationResponse, tags=["jobs-utils"])
@limiter.limit("10/15minutes")
async def verify_job_modification_code_route(
    request: Request,
    job_id: uuid.UUID,
    payload: schemas.JobModificationCodePayload,
    db: Session = Depends(get_db)
):
    """
    Verifies the modification code for a given job ID.
    Returns 200 OK with verified: true if correct.
    Returns 200 OK with verified: false and an error message if incorrect.
    Job not found will result in a 404 (handled by NotFoundError raised from CRUD).
    """
    try:
        # crud.verify_modification_code now returns bool, or raises NotFoundError
        is_correct = crud.verify_modification_code(db=db, job_id=job_id, modification_code=payload.modification_code)
        
        if is_correct:
            return schemas.JobVerificationResponse(verified=True, error=None)
        else:
            # Job was found, but the code was incorrect
            return schemas.JobVerificationResponse(verified=False, error="Incorrect modification code.")
    except NotFoundError:
        # Re-raise NotFoundError. It will be caught by your global error handler
        # (or FastAPI's default) and turned into a 404 response.
        raise
