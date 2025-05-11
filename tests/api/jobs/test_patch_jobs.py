import uuid
import time
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import crud
import schemas
import models
from utils import generate_modification_code

def test_update_job_success(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test successfully updating a job with a valid modification code.
    PRD 6.1: PATCH /api/jobs/{job_uuid} updates job details.
    """
    # 1. Create a job to update
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    # Store the original values for comparison
    original_title = db_job.title
    
    # 2. Give time gap to ensure updated_at will be different
    time.sleep(0.1)
    
    # 3. Update the job
    update_data = {
        "title": "Updated Job Title",
        "location": "Updated Location"
    }
    
    # Using the actual modification code which should be exactly 8 chars
    response = client.patch(
        f"/api/jobs/{db_job.id}",
        json=update_data,
        headers={"X-Modification-Code": db_job.modification_code}
    )
    
    # 4. Verify response status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    
    # 5. Verify response data
    updated_job = response.json()
    assert updated_job["title"] == update_data["title"], "Title should be updated"
    assert updated_job["location"] == update_data["location"], "Location should be updated"
    
    # 6. Verify fields not included in update remain unchanged
    assert updated_job["company_name"] == db_job.company_name, "Company name should remain unchanged"
    assert updated_job["description"] == db_job.description, "Description should remain unchanged"
    
    # 7. Refresh database record and verify it's updated
    db_session.refresh(db_job)
    assert db_job.title == update_data["title"], "Title should be updated in database"
    assert db_job.location == update_data["location"], "Location should be updated in database"

def test_update_job_html_sanitation(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test that HTML in description is sanitized when updating a job.
    PRD 6.3: HTML in description should be sanitized.
    """
    # 1. Create a job to update
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    # 2. Update the job with HTML content
    unsafe_html = """
    <p>Safe paragraph</p>
    <script>alert('Unsafe script')</script>
    <a href="javascript:alert('Unsafe link')">Click me</a>
    """
    
    update_data = {
        "description": unsafe_html
    }
    
    response = client.patch(
        f"/api/jobs/{db_job.id}",
        json=update_data,
        headers={"X-Modification-Code": db_job.modification_code}
    )
    
    # 3. Verify response status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    
    # 4. Verify HTML has been sanitized in response
    updated_job = response.json()
    sanitized_description = updated_job["description"]
    
    # Safe HTML elements should remain
    assert "<p>Safe paragraph</p>" in sanitized_description, "Safe HTML should be preserved"
    
    # Unsafe elements should be removed
    assert "<script>" not in sanitized_description, "Script tag should be removed"
    
    # 5. Verify HTML is sanitized in database
    db_session.refresh(db_job)
    assert db_job.description == sanitized_description, "Database record should contain sanitized HTML"

def test_update_job_missing_modification_code(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test that updating a job without a modification code fails.
    PRD 6.7: Attempting to update a job without a valid modification code should be unauthorized.
    """
    # 1. Create a job to update
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    # 2. Attempt to update without modification code
    update_data = {
        "title": "Unauthorized Update"
    }
    
    response = client.patch(
        f"/api/jobs/{db_job.id}",
        json=update_data
    )
    
    # 3. Verify response status code (expect 422 because modification_code header is required)
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # 4. Verify job was not updated in database
    db_session.refresh(db_job)
    assert db_job.title != update_data["title"], "Job title should not be updated without modification code"

def test_update_job_invalid_modification_code(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test that updating a job with an incorrect modification code fails.
    PRD 6.7: Attempting to update a job with an invalid modification code should be unauthorized.
    """
    # 1. Create a job to update
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    # 2. Attempt to update with incorrect modification code (must be 8 chars)
    update_data = {
        "title": "Unauthorized Update"
    }
    
    incorrect_code = "ABCD1234"  # 8 characters but not the correct code
    response = client.patch(
        f"/api/jobs/{db_job.id}",
        json=update_data,
        headers={"X-Modification-Code": incorrect_code}
    )
    
    # 3. Verify response (should be 403 after validation)
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
    
    # 4. Verify job was not updated in database
    db_session.refresh(db_job)
    assert db_job.title != update_data["title"], "Job title should not be updated with incorrect modification code"

def test_update_job_not_found(client: TestClient):
    """
    Test updating a non-existent job.
    Should return 404 Not Found.
    """
    # 1. Generate a random UUID that doesn't exist in the database
    non_existent_id = str(uuid.uuid4())
    
    # 2. Attempt to update a non-existent job
    update_data = {
        "title": "Update Non-existent Job"
    }
    
    response = client.patch(
        f"/api/jobs/{non_existent_id}",
        json=update_data,
        headers={"X-Modification-Code": "ABCD1234"}  # 8 chars to pass validation
    )
    
    # 3. Verify response status code
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"

def test_update_job_validation_errors(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test validation errors when updating a job.
    Should return 422 Unprocessable Entity.
    """
    # 1. Create a job to update
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    # 2. Try updating with invalid data (exceeding max length)
    invalid_data = {
        "title": "A" * 101  # Title max length is 100
    }
    
    response = client.patch(
        f"/api/jobs/{db_job.id}",
        json=invalid_data,
        headers={"X-Modification-Code": db_job.modification_code}
    )
    
    # 3. Verify response status code
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # 4. Verify job was not updated in database
    db_session.refresh(db_job)
    assert db_job.title != invalid_data["title"], "Job title should not be updated with invalid data"