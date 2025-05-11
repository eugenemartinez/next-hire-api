import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import crud
import schemas
import models
from utils import generate_modification_code

def test_delete_job_success(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test successfully deleting a job with a valid modification code.
    PRD 6.1: DELETE /api/jobs/{job_uuid} removes a job.
    """
    # Create a job to delete
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    job_id = str(db_job.id)
    mod_code = db_job.modification_code
    
    # Delete the job
    response = client.delete(
        f"/api/jobs/{job_id}",
        headers={"X-Modification-Code": mod_code}
    )
    
    # Verify response code (200 OK with message)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Verify response structure
    response_data = response.json()
    assert "message" in response_data, "Response should contain 'message' field"
    assert "job_id" in response_data, "Response should contain 'job_id' field"
    assert response_data["job_id"] == job_id, "Response should contain the deleted job's ID"
    
    # Verify job is deleted from database
    # Need to use a method that doesn't raise NotFoundError
    deleted_job = db_session.query(models.Job).filter(models.Job.id == job_id).first()
    assert deleted_job is None, "Job should be removed from database"

def test_delete_job_missing_modification_code(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test deleting a job without providing a modification code.
    PRD 6.7: Attempting to delete a job without a valid modification code should return 422.
    """
    # Create a job to delete
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    job_id = str(db_job.id)
    
    # Attempt to delete without modification code
    response = client.delete(f"/api/jobs/{job_id}")
    
    # Should return 422 Unprocessable Entity since the header is required by FastAPI validation
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # Verify job still exists in database
    existing_job = db_session.query(models.Job).filter(models.Job.id == job_id).first()
    assert existing_job is not None, "Job should still exist in database"

def test_delete_job_invalid_modification_code(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test deleting a job with an incorrect modification code.
    PRD 6.7: Attempting to delete a job with an invalid modification code returns 403 Forbidden.
    """
    # Create a job to delete
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    job_id = str(db_job.id)
    
    # Attempt to delete with incorrect modification code (8 chars as required)
    response = client.delete(
        f"/api/jobs/{job_id}",
        headers={"X-Modification-Code": "WRONGCOD"}  # 8-char code but incorrect
    )
    
    # Should return 403 Forbidden due to incorrect modification code
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
    
    # Verify error response format
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    assert "Incorrect modification code" in error_response["detail"], "Error should mention incorrect code"
    
    # Verify job still exists in database
    existing_job = db_session.query(models.Job).filter(models.Job.id == job_id).first()
    assert existing_job is not None, "Job should still exist in database"

def test_delete_job_not_found(client: TestClient):
    """
    Test deleting a non-existent job.
    Should return 404 Not Found.
    """
    # Generate a random UUID that doesn't exist in the database
    non_existent_id = str(uuid.uuid4())
    
    # Attempt to delete a non-existent job
    response = client.delete(
        f"/api/jobs/{non_existent_id}",
        headers={"X-Modification-Code": "ABCD1234"}  # Any 8-char code
    )
    
    # Verify response status code
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"
    
    # Verify error response format
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    assert "not found" in error_response["detail"].lower(), "Error should mention job not found"