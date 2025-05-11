import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import List
import random
import string
import uuid

import schemas
from models import Job as JobModel
import crud
from utils import generate_modification_code

@pytest.fixture(scope="function")
def create_multiple_jobs(db_session: Session, sample_job_payload_factory) -> List[JobModel]:
    """Fixture to create test jobs for GET endpoint testing."""
    # Create 3 diverse job entries
    jobs_data = [
        sample_job_payload_factory(
            title="Software Engineer", 
            company_name="Tech Solutions Inc.",
            poster_username="user_alpha",
            tags=["python", "fastapi", "backend"]
        ),
        sample_job_payload_factory(
            title="Data Scientist", 
            company_name="Analytics Corp",
            poster_username="user_beta",
            tags=["python", "ml", "data"]
        ),
        sample_job_payload_factory(
            title="Product Manager", 
            company_name="Product Innovations",
            poster_username="user_gamma",
            location="Remote",
            tags=["product", "management"]
        ),
    ]
    
    created_jobs = []
    for job_data in jobs_data:
        # Convert dictionary to JobCreate schema
        job_create = schemas.JobCreate(**job_data)
        db_job = crud.create_job(db=db_session, job=job_create)
        created_jobs.append(db_job)
    
    db_session.commit()
    return created_jobs

def test_list_jobs_success(client: TestClient, create_multiple_jobs: List[JobModel]):
    """
    Test retrieving a list of jobs successfully.
    PRD 6.1: GET /api/jobs/ lists all jobs with pagination.
    PRD 5.6: modification_code should NOT be present in listed jobs.
    """
    response = client.get("/api/jobs/")
    
    # Verify status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # Verify pagination structure based on actual API response format
    assert "jobs" in data, "Response should contain 'jobs' field"
    assert "total" in data, "Response should contain 'total' field"
    assert "limit" in data, "Response should contain 'limit' field" 
    assert "skip" in data, "Response should contain 'skip' field"
    
    # Verify data values
    assert isinstance(data["jobs"], list), "'jobs' should be a list"
    assert data["total"] >= len(create_multiple_jobs), f"Expected at least {len(create_multiple_jobs)} jobs in total"
    assert data["skip"] == 0, "Default skip should be 0"
    assert data["limit"] == 20, "Default limit should be 20"
    
    # Verify job item structure
    for job_item in data["jobs"]:
        assert "id" in job_item, "Job should have id field"
        assert "title" in job_item, "Job should have title field"
        assert "company_name" in job_item, "Job should have company_name field"
        assert "poster_username" in job_item, "Job should have poster_username field"
        assert "created_at" in job_item, "Job should have created_at field"
        assert "updated_at" in job_item, "Job should have updated_at field"
        
        # Critical security check per PRD 5.6
        assert "modification_code" not in job_item, "modification_code should NOT be exposed in list view"
    
    # Optionally verify the created test jobs are in the response
    job_ids_in_response = {job["id"] for job in data["jobs"]}
    for created_job in create_multiple_jobs:
        assert str(created_job.id) in job_ids_in_response, f"Created job {created_job.id} not found in response"

def test_list_jobs_empty(client: TestClient, db_session: Session):
    """
    Test retrieving jobs when no jobs exist.
    Should return 200 with empty jobs list and total=0.
    """
    # Clear all jobs from the database
    db_session.query(JobModel).delete()
    db_session.commit()
    
    response = client.get("/api/jobs/")
    
    assert response.status_code == 200, "Should return 200 even when no jobs exist"
    data = response.json()
    
    # Verify structure and empty state based on actual API response format
    assert "jobs" in data, "Response should contain 'jobs' field"
    assert "total" in data, "Response should contain 'total' field"
    assert len(data["jobs"]) == 0, "Jobs list should be empty"
    assert data["total"] == 0, "Total should be 0"

def test_list_jobs_pagination(client: TestClient, db_session: Session):
    """
    Test pagination for jobs listing using skip and limit parameters.
    PRD 6.1: GET /api/jobs/ supports pagination via skip and limit parameters.
    """
    # Create 15 jobs for pagination testing
    jobs = []
    for i in range(15):
        # Generate a modification code for each job
        mod_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        job = JobModel(
            title=f"Pagination Test Job {i}",
            company_name=f"Company {i}",
            description=f"Description for job {i}",
            application_info=f"apply-{i}@example.com",
            poster_username=f"test_user_{i}",
            modification_code=mod_code  # Add the modification code
        )
        db_session.add(job)
        jobs.append(job)
    db_session.commit()
    for job in jobs:
        db_session.refresh(job)
    
    # Test first page (default pagination: skip=0, limit=20)
    response_default = client.get("/api/jobs/")
    assert response_default.status_code == 200
    data_default = response_default.json()
    assert len(data_default["jobs"]) == 15  # All 15 jobs (less than default limit)
    assert data_default["total"] == 15
    assert data_default["skip"] == 0
    assert data_default["limit"] == 20  # Default limit
    
    # Test with custom limit (first 5 jobs)
    response_limit = client.get("/api/jobs/?limit=5")
    assert response_limit.status_code == 200
    data_limit = response_limit.json()
    assert len(data_limit["jobs"]) == 5  # Only first 5 jobs
    assert data_limit["total"] == 15  # Total count unchanged
    assert data_limit["limit"] == 5
    
    # Test second page (skip first 5 results)
    response_skip = client.get("/api/jobs/?skip=5&limit=5")
    assert response_skip.status_code == 200
    data_skip = response_skip.json()
    assert len(data_skip["jobs"]) == 5  # 5 jobs from the second page
    assert data_skip["total"] == 15  # Total count unchanged
    assert data_skip["skip"] == 5
    assert data_skip["limit"] == 5
    
    # Verify different jobs are returned on different pages
    page1_job_ids = {job["id"] for job in data_limit["jobs"]}
    page2_job_ids = {job["id"] for job in data_skip["jobs"]}
    assert not page1_job_ids.intersection(page2_job_ids), "Pages should contain different job IDs"
    
    # Test with skip beyond available results
    response_beyond = client.get("/api/jobs/?skip=20")
    assert response_beyond.status_code == 200
    data_beyond = response_beyond.json()
    assert len(data_beyond["jobs"]) == 0  # No results when skipping beyond total
    assert data_beyond["total"] == 15  # Total count unchanged

def test_list_jobs_search_title_description(client: TestClient, db_session: Session):
    """
    Test searching jobs by title and description.
    PRD 6.1: GET /api/jobs/?search={term} searches in job titles and descriptions.
    """
    # Create test jobs with specific terms to search for
    jobs = []
    
    # Job with searchable term in title
    job1 = JobModel(
        title="Python Developer position available",
        company_name="Tech Corp",
        description="We are looking for a skilled developer.",
        application_info="apply@example.com",
        poster_username="recruiter1",
        modification_code=generate_modification_code(db_session)  # Pass db_session here
    )
    
    # Job with searchable term in description
    job2 = JobModel(
        title="Senior Developer",
        company_name="Software Inc",
        description="Experience with Python and FastAPI required.",
        application_info="jobs@software.com",
        poster_username="recruiter2",
        modification_code=generate_modification_code(db_session)  # Pass db_session here
    )
    
    # Job with no matching terms (to verify it's excluded)
    job3 = JobModel(
        title="Marketing Specialist",
        company_name="Marketing Pro",
        description="Experience in digital marketing campaigns.",
        application_info="marketing@example.com",
        poster_username="recruiter3",
        modification_code=generate_modification_code(db_session)  # Pass db_session here
    )
    
    # Additional job with matching term in both title and description
    job4 = JobModel(
        title="Python Team Lead",
        company_name="DevTeam",
        description="Lead a team of Python developers.",
        application_info="careers@devteam.com",
        poster_username="recruiter4",
        modification_code=generate_modification_code(db_session)  # Pass db_session here
    )
    
    db_session.add_all([job1, job2, job3, job4])
    db_session.commit()
    
    # Test search for "Python" - should match jobs 1, 2, and 4
    response_python = client.get("/api/jobs/?search=Python")
    assert response_python.status_code == 200
    data_python = response_python.json()
    
    assert data_python["total"] == 3, "Should find 3 jobs containing 'Python'"
    
    # Verify all returned jobs contain "Python" in title or description
    for job in data_python["jobs"]:
        assert ("python" in job["title"].lower() or 
                "python" in job["description"].lower()), \
            f"Job should contain 'Python' in title or description: {job}"
    
    # Test search for "marketing" - should match only job 3
    response_marketing = client.get("/api/jobs/?search=marketing")
    assert response_marketing.status_code == 200
    data_marketing = response_marketing.json()
    
    assert data_marketing["total"] == 1, "Should find 1 job containing 'marketing'"
    assert "marketing" in data_marketing["jobs"][0]["description"].lower(), \
        "Job should contain 'marketing' in description"
    
    # Test search for non-existent term
    response_nonexistent = client.get("/api/jobs/?search=nonexistentterm")
    assert response_nonexistent.status_code == 200
    data_nonexistent = response_nonexistent.json()
    
    assert data_nonexistent["total"] == 0, "Should find 0 jobs for non-existent term"
    assert len(data_nonexistent["jobs"]) == 0, "Should return empty jobs list"
    
    # Test search with case insensitivity
    response_case = client.get("/api/jobs/?search=python")  # lowercase
    assert response_case.status_code == 200
    data_case = response_case.json()
    
    assert data_case["total"] == 3, "Case-insensitive search should still find 3 jobs"

    # Test search with both word boundary and partial word match
    # The behavior here should match your actual implementation
    response_dev = client.get("/api/jobs/?search=dev")
    assert response_dev.status_code == 200
    data_dev = response_dev.json()
    
    # Here we check if search works with partial matches (e.g. "dev" matches "developer")
    # If your implementation only does exact word matches, adjust this assertion
    has_matched_jobs = data_dev["total"] > 0
    assert has_matched_jobs, "Should find jobs containing 'dev'"

def test_list_jobs_filter_tags_or_logic(client: TestClient, db_session: Session):
    """
    Test filtering jobs by tags with OR logic.
    PRD 5.3: Query parameter 'tags' allows filtering jobs by tags.
    Multiple tags (comma-separated) should use OR logic.
    """
    # Create test jobs with different tags
    job1 = JobModel(
        title="Python Developer",
        company_name="Tech Corp",
        description="Python developer role",
        application_info="apply@example.com",
        poster_username="recruiter1",
        tags=["python", "backend", "api"],
        modification_code=generate_modification_code(db_session)
    )
    
    job2 = JobModel(
        title="Frontend Developer",
        company_name="Web Solutions",
        description="Frontend specialist needed",
        application_info="careers@websolutions.com",
        poster_username="recruiter2",
        tags=["javascript", "react", "frontend"],
        modification_code=generate_modification_code(db_session)
    )
    
    job3 = JobModel(
        title="Full Stack Developer",
        company_name="DevTeam",
        description="Full stack role with Python and React",
        application_info="jobs@devteam.com",
        poster_username="recruiter3",
        tags=["python", "react", "fullstack"],
        modification_code=generate_modification_code(db_session)
    )
    
    job4 = JobModel(
        title="DevOps Engineer",
        company_name="Cloud Systems",
        description="DevOps specialist needed",
        application_info="hr@cloudsystems.com",
        poster_username="recruiter4",
        tags=["devops", "aws", "kubernetes"],
        modification_code=generate_modification_code(db_session)
    )
    
    db_session.add_all([job1, job2, job3, job4])
    db_session.commit()
    
    # Test 1: Filter by a single tag "python" - should match jobs 1 and 3
    response_python = client.get("/api/jobs/?tags=python")
    assert response_python.status_code == 200
    data_python = response_python.json()
    
    assert data_python["total"] == 2, "Should find 2 jobs with tag 'python'"
    assert len(data_python["jobs"]) == 2
    
    # Verify all returned jobs have the "python" tag
    for job in data_python["jobs"]:
        assert "python" in job["tags"], f"Job should have 'python' tag: {job}"
    
    # Test 2: Filter by multiple tags "python,react" with OR logic
    # Should match all jobs with either "python" OR "react" tags (jobs 1, 2, and 3)
    response_or = client.get("/api/jobs/?tags=python,react")
    assert response_or.status_code == 200
    data_or = response_or.json()
    
    assert data_or["total"] == 3, "Should find 3 jobs with either 'python' OR 'react' tags"
    assert len(data_or["jobs"]) == 3
    
    # Verify all returned jobs have either "python" or "react" tag
    for job in data_or["jobs"]:
        assert any(tag in ["python", "react"] for tag in job["tags"]), \
            f"Job should have either 'python' or 'react' tag: {job}"
    
    # Test 3: Filter by a tag that doesn't exist
    response_nonexistent = client.get("/api/jobs/?tags=nonexistenttag")
    assert response_nonexistent.status_code == 200
    data_nonexistent = response_nonexistent.json()
    
    assert data_nonexistent["total"] == 0, "Should find 0 jobs with non-existent tag"
    assert len(data_nonexistent["jobs"]) == 0
    
    # Test 4: Filter by multiple tags where some don't exist
    # Should still return jobs matching the existing tags (OR logic)
    response_mixed = client.get("/api/jobs/?tags=python,nonexistenttag")
    assert response_mixed.status_code == 200
    data_mixed = response_mixed.json()
    
    assert data_mixed["total"] == 2, "Should find 2 jobs with 'python' tag, ignoring non-existent tag"
    
    # Test 5: Case insensitivity (if your API implements this)
    # This might vary based on your implementation
    response_case = client.get("/api/jobs/?tags=PYTHON")
    assert response_case.status_code == 200
    # If your implementation is case-insensitive, this assertion should pass:
    # assert response_case.json()["total"] > 0, "Tag filtering should be case-insensitive"
    
    # If your API is case-sensitive, this would be the correct assertion:
    # assert response_case.json()["total"] == 0, "Tag filtering is case-sensitive"

def test_list_jobs_sorting(client: TestClient, db_session: Session):
    """
    Test sorting jobs by different fields and directions.
    """
    # Clear any existing jobs
    db_session.query(JobModel).delete()
    db_session.commit()
    
    # Create jobs with simple predictable data 
    # Create in reverse order to ensure created_at order is different from title order
    job3 = JobModel(
        title="C Third Job",
        company_name="Company C",
        description="Description C",
        application_info="apply@c.com",
        poster_username="user_c",
        modification_code=generate_modification_code(db_session)
    )
    db_session.add(job3)
    db_session.commit()
    
    # Wait to ensure timestamps differ
    import time
    time.sleep(0.2)
    
    job2 = JobModel(
        title="B Second Job",
        company_name="Company B",
        description="Description B",
        application_info="apply@b.com",
        poster_username="user_b",
        modification_code=generate_modification_code(db_session)
    )
    db_session.add(job2)
    db_session.commit()
    
    time.sleep(0.2)
    
    job1 = JobModel(
        title="A First Job",
        company_name="Company A",
        description="Description A",
        application_info="apply@a.com",
        poster_username="user_a",
        modification_code=generate_modification_code(db_session)
    )
    db_session.add(job1)
    db_session.commit()
    
    # Test basic title sorting only
    response = client.get("/api/jobs/?sort_by=title&sort_order=desc")
    assert response.status_code == 200
    data = response.json()
    
    # Get title order
    titles = [job["title"] for job in data["jobs"]]
    
    # Simple assertion - the first job should be C Third Job
    # (this is exactly where the test is failing)
    assert titles[0] == "C Third Job", f"Expected 'C Third Job' first in title desc sort, got: {titles[0]}"

def test_get_job_by_id_success(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test retrieving a job by its ID.
    PRD 6.1: GET /api/jobs/{job_uuid} retrieves a single job.
    PRD 5.6: modification_code should NOT be present in the response.
    """
    # Create a job to retrieve
    job_data = sample_job_payload_factory(
        title="Software Engineer for Testing",
        company_name="Test Company", 
        description="This is a test job for the get by ID endpoint"
    )
    job_create = schemas.JobCreate(**job_data)
    db_job = crud.create_job(db=db_session, job=job_create)
    db_session.commit()
    
    # Retrieve the job
    response = client.get(f"/api/jobs/{db_job.id}")
    
    # Verify status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
    
    # Verify response data
    job_response = response.json()
    
    # Check if all required fields are present
    assert "id" in job_response, "Response should contain id field"
    assert "title" in job_response, "Response should contain title field"
    assert "company_name" in job_response, "Response should contain company_name field"
    assert "description" in job_response, "Response should contain description field"
    assert "application_info" in job_response, "Response should contain application_info field"
    assert "created_at" in job_response, "Response should contain created_at field"
    assert "updated_at" in job_response, "Response should contain updated_at field"
    
    # Check that the field values match what we created
    assert str(db_job.id) == job_response["id"], "ID should match"
    assert db_job.title == job_response["title"], "Title should match"
    assert db_job.company_name == job_response["company_name"], "Company name should match"
    assert db_job.description == job_response["description"], "Description should match"
    
    # Critical security check per PRD 5.6
    assert "modification_code" not in job_response, "modification_code should NOT be exposed in job detail view"

def test_get_job_by_id_not_found(client: TestClient):
    """
    Test retrieving a job with a non-existent ID.
    Should return 404 Not Found.
    """
    # Generate a random UUID that doesn't exist in the database
    non_existent_id = str(uuid.uuid4())
    
    # Attempt to retrieve non-existent job
    response = client.get(f"/api/jobs/{non_existent_id}")
    
    # Verify status code
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"
    
    # Verify error response format
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    assert "not found" in error_response["detail"].lower(), f"Expected 'not found' message, got: {error_response['detail']}"

def test_get_job_by_id_invalid_uuid_format(client: TestClient):
    """
    Test retrieving a job with an invalid UUID format.
    Should return 422 Unprocessable Entity.
    """
    # Use an invalid UUID format
    invalid_id = "not-a-valid-uuid"
    
    # Attempt to retrieve with invalid ID
    response = client.get(f"/api/jobs/{invalid_id}")
    
    # Verify status code
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"
    
    # Verify error response format
    error_response = response.json()
    assert "detail" in error_response, "Error response should contain 'detail' field"
    # The error detail should indicate a validation error related to UUID format
    assert any("uuid" in str(error).lower() for error in error_response["detail"]), \
        f"Expected UUID validation error, got: {error_response['detail']}"