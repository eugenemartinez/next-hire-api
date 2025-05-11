import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import crud
import schemas
import models

def test_get_unique_tags_success(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test retrieving a list of unique tags from existing jobs.
    PRD 6.1: GET /api/tags returns a list of all unique tags.
    """
    # Create several jobs with different tags
    job1_data = sample_job_payload_factory(tags=["python", "fastapi", "backend"])
    job2_data = sample_job_payload_factory(tags=["python", "react", "frontend"])
    job3_data = sample_job_payload_factory(tags=["react", "typescript", "frontend"])
    
    # Add jobs to the database
    for job_data in [job1_data, job2_data, job3_data]:
        job_create = schemas.JobCreate(**job_data)
        db_job = crud.create_job(db=db_session, job=job_create)
        db_session.commit()
    
    # Request unique tags
    response = client.get("/api/tags")
    
    # Assert status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Assert response structure
    tags = response.json()
    assert isinstance(tags, list), "Response should be a list"
    
    # Assert content - should have all unique tags from our jobs
    expected_tags = ["python", "fastapi", "backend", "react", "frontend", "typescript"]
    
    # Check each expected tag is in the response
    # Note: not using exact equality because there might be other tags from previous tests
    for tag in expected_tags:
        assert tag in tags, f"Expected tag '{tag}' not found in response"
    
    # Check that duplicate tags are only returned once
    assert len(set(tags)) == len(tags), "Response contains duplicate tags"

def test_get_unique_tags_no_jobs_or_tags(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test retrieving tags when no jobs or no jobs with tags exist.
    Should return 200 OK with empty array.
    """
    # First clear all jobs from the test database
    db_session.query(models.Job).delete()
    db_session.commit()
    
    # Request unique tags
    response = client.get("/api/tags")
    
    # Assert status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Assert response is an empty list
    tags = response.json()
    assert isinstance(tags, list), "Response should be a list"
    assert len(tags) == 0, "Response should be an empty list when no jobs exist"
    
    # Create a job with no tags
    job_data = sample_job_payload_factory(tags=[])
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    # Request unique tags again
    response = client.get("/api/tags")
    
    # Assert still returns empty list when jobs exist but have no tags
    tags = response.json()
    assert isinstance(tags, list), "Response should be a list"
    assert len(tags) == 0, "Response should be an empty list when jobs have no tags"