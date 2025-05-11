import uuid
import json
from typing import List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import crud
import schemas
import models
from utils import generate_modification_code

def test_get_saved_jobs_success(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test retrieving multiple jobs by list of valid UUIDs.
    PRD 6.1: POST /api/jobs/saved retrieves batch job details.
    """
    # Create 3 jobs to retrieve
    job_ids = []
    for i in range(3):
        job_data = sample_job_payload_factory(
            title=f"Saved Job {i+1}",
            company_name=f"Company {i+1}"
        )
        job_create = schemas.JobCreate(**job_data)
        db_job = crud.create_job(db=db_session, job=job_create)
        db_session.commit()
        job_ids.append(str(db_job.id))
    
    # Request saved jobs
    response = client.post(
        "/api/jobs/saved",
        json={"job_ids": job_ids}
    )
    
    # Assert status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Assert response structure
    saved_jobs = response.json()
    assert isinstance(saved_jobs, list), "Response should be a list"
    assert len(saved_jobs) == 3, f"Expected 3 jobs, got {len(saved_jobs)}"
    
    # Assert job details are correct
    for i, job in enumerate(saved_jobs):
        assert job["title"] == f"Saved Job {i+1}", f"Expected 'Saved Job {i+1}', got {job['title']}"
        assert job["company_name"] == f"Company {i+1}", f"Expected 'Company {i+1}', got {job['company_name']}"
        
        # Assert modification_code is NOT present
        assert "modification_code" not in job, "modification_code should not be present in job details"

def test_get_saved_jobs_empty_list_input(client: TestClient):
    """
    Test retrieving jobs with an empty list of job_ids.
    Should return 200 OK with an empty array.
    """
    # Request with empty job_ids list
    response = client.post(
        "/api/jobs/saved",
        json={"job_ids": []}
    )
    
    # Assert status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Assert response is an empty list
    saved_jobs = response.json()
    assert isinstance(saved_jobs, list), "Response should be a list"
    assert len(saved_jobs) == 0, "Response should be an empty list"

def test_get_saved_jobs_some_non_existent_ids(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test retrieving jobs with a mix of valid and non-existent UUIDs.
    Should return 200 OK with only the existing jobs.
    """
    # Create 2 real jobs
    real_job_ids = []
    for i in range(2):
        job_data = sample_job_payload_factory(
            title=f"Real Job {i+1}",
            company_name=f"Real Company {i+1}"
        )
        job_create = schemas.JobCreate(**job_data)
        db_job = crud.create_job(db=db_session, job=job_create)
        db_session.commit()
        real_job_ids.append(str(db_job.id))
    
    # Add 2 non-existent UUIDs
    fake_job_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    all_job_ids = real_job_ids + fake_job_ids
    
    # Request jobs with mixed IDs
    response = client.post(
        "/api/jobs/saved",
        json={"job_ids": all_job_ids}
    )
    
    # Assert status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Assert only real jobs are returned
    saved_jobs = response.json()
    assert isinstance(saved_jobs, list), "Response should be a list"
    assert len(saved_jobs) == 2, f"Expected 2 jobs (only real ones), got {len(saved_jobs)}"
    
    # Verify returned jobs match real ones
    job_titles = [job["title"] for job in saved_jobs]
    assert "Real Job 1" in job_titles, "Expected 'Real Job 1' in results"
    assert "Real Job 2" in job_titles, "Expected 'Real Job 2' in results"

def test_get_saved_jobs_invalid_uuid_format_in_list(client: TestClient):
    """
    Test retrieving jobs with an invalid UUID format in the list.
    Should return 422 Unprocessable Entity.
    """
    # Request with invalid UUID format
    response = client.post(
        "/api/jobs/saved",
        json={"job_ids": ["not-a-valid-uuid", str(uuid.uuid4())]}
    )
    
    # Assert status code
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # Assert error details mention UUID validation
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    
    # Check error details for UUID format mention
    assert any("uuid" in str(error).lower() for error in error_response["detail"]), \
        f"Expected UUID validation error, got: {error_response['detail']}"

def test_get_saved_jobs_invalid_payload_format(client: TestClient):
    """
    Test retrieving jobs with incorrect payload structure.
    Should return 422 Unprocessable Entity.
    """
    # Request with incorrect payload structure
    response = client.post(
        "/api/jobs/saved",
        json={"wrong_field": [str(uuid.uuid4())]}
    )
    
    # Assert status code
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # Assert error details mention required field
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    
    # Check error details for field validation
    assert any("job_ids" in str(error).lower() for error in error_response["detail"]), \
        f"Expected job_ids field validation error, got: {error_response['detail']}"