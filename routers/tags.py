from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging # Add this

# Corrected imports:
import crud  # Assumes crud.py is in the 'server' directory
import schemas  # Assumes schemas.py is in the 'server' directory
from core.database import get_db # Assumes get_db is in server/core/database.py

router = APIRouter(
    prefix="/tags",  # This will be combined with settings.API_V1_STR by main.py
    tags=["tags"],   # Tag for OpenAPI documentation
    responses={404: {"description": "Not found"}}, # Default response for this router
)

@router.get("/", response_model=List[str])
def read_all_unique_tags(db: Session = Depends(get_db)):
    """
    Retrieves a list of all unique tags used across all jobs.
    """
    try:
        unique_tags = crud.get_unique_tags(db=db)
        return unique_tags
    except Exception as e:
        logger = logging.getLogger(__name__) # Or your Structlog logger if configured for use here
        logger.error("Error retrieving tags", exc_info=e) # This will log the exception details
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving tags."
        )