import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import crud
import schemas
import models

def test_verify_modification_code_success(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test verification with a correct job_uuid and modification_code.
    PRD 6.1: POST /api/jobs/{job_uuid}/verify should return verified: true for correct codes.
    """
    # Create a job to verify
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    job_id = str(db_job.id)
    mod_code = db_job.modification_code
    
    # Verify the modification code
    response = client.post(
        f"/api/jobs/{job_id}/verify",
        json={"modification_code": mod_code}
    )
    
    # Verify response code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Verify response data
    verify_response = response.json()
    assert verify_response["verified"] is True, "Expected verified: true"
    assert verify_response["error"] is None, "Expected error: null when verified"

def test_verify_modification_code_incorrect_code(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test verification with a correct job_uuid but incorrect modification_code.
    Should return verified: false with error message.
    """
    # Create a job to verify
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    job_id = str(db_job.id)
    # Use an incorrect code (ensure 8 characters to pass validation)
    incorrect_code = "WRONGCOD"
    
    # Verify with incorrect code
    response = client.post(
        f"/api/jobs/{job_id}/verify",
        json={"modification_code": incorrect_code}
    )
    
    # Should return 200 OK with verified: false (not a 403 error)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    # Verify response data
    verify_response = response.json()
    assert verify_response["verified"] is False, "Expected verified: false"
    assert verify_response["error"] is not None, "Expected error message"
    assert "incorrect" in verify_response["error"].lower(), "Error should indicate incorrect code"

def test_verify_modification_code_job_not_found(client: TestClient):
    """
    Test verification for a non-existent job_uuid.
    Should return 404 Not Found.
    """
    # Generate a random UUID that doesn't exist in the database
    non_existent_id = str(uuid.uuid4())
    
    # Use a valid 8-character code to pass validation
    # so we can test the actual 404 for non-existent job
    response = client.post(
        f"/api/jobs/{non_existent_id}/verify",
        json={"modification_code": "TEST1234"}  # Exactly 8 characters
    )
    
    # Verify response code
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"
    
    # Verify error response format
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    assert "not found" in error_response["detail"].lower(), "Error should indicate job not found"

def test_verify_modification_code_missing_code_in_payload(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test verification without modification_code in the payload.
    Should return 422 Unprocessable Entity.
    """
    # Create a job to verify
    job_data = sample_job_payload_factory()
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    job_id = str(db_job.id)
    
    # Send empty payload
    response = client.post(
        f"/api/jobs/{job_id}/verify",
        json={}
    )
    
    # Should return 422 Unprocessable Entity for validation error
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # Check error details for field validation
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    assert any("modification_code" in str(error).lower() for error in error_response["detail"]), \
        f"Expected modification_code field validation error, got: {error_response['detail']}"

def test_verify_modification_code_invalid_uuid_format(client: TestClient):
    """
    Test verification with an invalid job_uuid format.
    Should return 422 Unprocessable Entity.
    """
    # Use an invalid UUID format
    invalid_id = "not-a-valid-uuid"
    
    # Attempt verification with invalid job ID
    response = client.post(
        f"/api/jobs/{invalid_id}/verify",
        json={"modification_code": "TESTCODE8"}
    )
    
    # Should return 422 Unprocessable Entity for UUID format validation
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # Check error details for UUID validation
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    assert any("uuid" in str(error).lower() for error in error_response["detail"]), \
        f"Expected UUID validation error, got: {error_response['detail']}"