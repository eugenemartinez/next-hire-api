import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session # Assuming you might use it directly in some tests
from typing import Any
from crud import MAX_JOB_POSTINGS_LIMIT # Import the constant

# Tests related to POST /api/jobs/

def test_create_job_success(client: TestClient, db_session: Session, sample_job_payload_factory):
    job_data = sample_job_payload_factory(
        title="Software Engineer Test",
        company_name="TestCorp",
        location="Testville",
        description="<h1>Test Description</h1><p>With HTML.</p><script>alert('xss')</script>",
        application_info="apply@testcorp.com",
        job_type="Full-time",
        tags=["python", "fastapi"]
    )
    response = client.post("/api/jobs/", json=job_data)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == job_data["title"]
    assert data["company_name"] == job_data["company_name"]
    assert "id" in data
    assert "modification_code" in data
    assert "poster_username" in data
    assert "<script>" not in data["description"]
    assert "<h1>" in data["description"]

    # Optionally, verify in DB
    # from models import Job as JobModel
    # db_job = db_session.query(JobModel).filter(JobModel.id == data["id"]).first()
    # assert db_job is not None
    # assert db_job.title == job_data["title"]

def test_create_job_with_optional_fields_omitted(client: TestClient, db_session: Session, sample_job_payload_factory):
    """
    Test creating a job successfully when optional fields are omitted.
    PRD 5.1: location, job_type, salary_min, salary_max, salary_currency, tags are optional.
    PRD 5.2: poster_username is generated if not provided.
    """
    job_data = sample_job_payload_factory(
        title="Intern Developer",
        company_name="Startup Inc.",
        description="A great learning opportunity.",
        application_info="careers@startup.com",
        # Omit optional fields by not providing them to the factory or setting to None if factory requires them
        location=None,
        job_type=None,
        salary_min=None,
        salary_max=None,
        salary_currency=None,
        tags=None, # Or [] depending on how your factory and model handle it
        poster_username=None # To test generation
    )
    # Clean up keys that should be truly absent if factory sets them to None by default
    for key in ["location", "job_type", "salary_min", "salary_max", "salary_currency", "tags", "poster_username"]:
        if job_data.get(key) is None: # Or however your factory indicates omission
            if key in job_data: del job_data[key]


    response = client.post("/api/jobs/", json=job_data)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["title"] == "Intern Developer" # Hardcoding for clarity as factory might change
    assert data["company_name"] == "Startup Inc."
    assert data["description"] == "A great learning opportunity."
    assert data["application_info"] == "careers@startup.com"

    assert "id" in data
    assert "modification_code" in data
    assert "poster_username" in data
    assert data["poster_username"] is not None

    assert data["location"] is None
    assert data["job_type"] is None
    assert data["salary_min"] is None
    assert data["salary_max"] is None
    assert data["salary_currency"] is None
    assert data["tags"] == []

    assert "created_at" in data
    assert "updated_at" in data

@pytest.mark.parametrize(
    "missing_field", ["title", "company_name", "description", "application_info"]
)
def test_create_job_missing_required_fields(client: TestClient, missing_field: str, sample_job_payload_factory):
    """
    Test creating a job fails with 422 if a required field is missing.
    PRD 6.3: title, company_name, description, application_info are required.
    """
    job_data = sample_job_payload_factory()
    del job_data[missing_field]

    response = client.post("/api/jobs/", json=job_data)

    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data
    found_error_for_field = False
    for error in data["detail"]:
        if missing_field in error.get("loc", []):
            assert error.get("type") == "missing"
            found_error_for_field = True
            break
    assert found_error_for_field, f"Error detail for missing field '{missing_field}' not found: {data['detail']}"

@pytest.mark.parametrize(
    "field_name, invalid_value, expected_error_type",
    [
        ("title", 123, "string_type"),
        ("company_name", True, "string_type"),
        ("description", {"text": "abc"}, "string_type"),
        ("application_info", "not-an-email-or-url", "url_parsing"), # Or value_error depending on Pydantic version/setup
        ("location", 123.45, "string_type"),
        ("job_type", "non_enum_value", "enum"),
        ("salary_min", "not-a-number", "int_parsing"),
        ("salary_max", [1,2,3], "int_type"), # Pydantic v2 might be 'int_type' or 'integer_type'
        ("salary_currency", 123, "enum"), # CHANGED: Was "string_type", now "enum" due to PopularCurrency Enum
        ("poster_username", 12345, "string_type"),
        ("tags", "not-a-list", "value_error"), # Assuming custom validator raises this
        ("tags", [1, "valid", 3], "value_error"), # Assuming custom validator raises this
    ],
)
def test_create_job_invalid_data_types(
    client: TestClient, field_name: str, invalid_value: Any, expected_error_type: str, sample_job_payload_factory
):
    """
    Test creating a job fails with 422 if data types are invalid.
    PRD 6.3: Data types are enforced.
    """
    job_data = sample_job_payload_factory() # Get a full valid payload
    job_data[field_name] = invalid_value # Set the invalid value

    response = client.post("/api/jobs/", json=job_data)

    assert response.status_code == 422, f"Expected 422 for {field_name}={invalid_value}, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert "detail" in data

    error_found_for_field = False
    for error in data["detail"]:
        current_error_loc = error.get("loc", [])
        field_in_loc = False
        if len(current_error_loc) > 1 and current_error_loc[0] == 'body':
            if current_error_loc[1] == field_name:
                field_in_loc = True
            elif len(current_error_loc) > 2 and current_error_loc[1] == field_name and isinstance(current_error_loc[2], int):
                 field_in_loc = True

        if field_in_loc:
            if expected_error_type.lower() in error.get("type", "").lower():
                 error_found_for_field = True
                 break
    assert error_found_for_field, f"Error detail for field '{field_name}' with type '{expected_error_type}' not found: {data['detail']}"

@pytest.mark.parametrize(
    "field_name, max_length, min_length",
    [
        ("title", 100, 1),
        ("company_name", 100, 1),
        ("location", 100, None), # Assuming location can be optional and thus no min_length if None
        ("description", 5000, 1),
        ("application_info", 255, 1), # Max length for the string representation
        ("poster_username", 50, 3),
        # ("salary_currency", 10, None), # REMOVED: Length for Enum is not tested this way. Enum validity is key.
    ],
)
def test_create_job_field_length_limits(
    client: TestClient, field_name: str, max_length: int, min_length: int | None, sample_job_payload_factory
):
    """
    Test creating a job fails with 422 if string fields exceed max length or are below min length.
    PRD 6.3: Field length limits are enforced.
    """
    base_job_data = sample_job_payload_factory()

    # Test exceeding max length
    job_data_too_long = base_job_data.copy() # Use copy for modification
    job_data_too_long[field_name] = "a" * (max_length + 1)

    if field_name == "application_info":
        if "@" in base_job_data.get(field_name, ""): # Check original type if exists
            job_data_too_long[field_name] = "a" * (max_length - 10) + "@example.com"
        else:
            job_data_too_long[field_name] = "http://" + "a" * (max_length - 10) + ".com"

    response_too_long = client.post("/api/jobs/", json=job_data_too_long)
    assert response_too_long.status_code == 422, f"Expected 422 for {field_name} exceeding max_length. Response: {response_too_long.text}"
    data_too_long = response_too_long.json()
    assert "detail" in data_too_long
    error_found_max = False
    for error in data_too_long["detail"]:
        if field_name in error.get("loc", []):
            error_type = error.get("type", "")
            error_msg = error.get("msg", "").lower()
            if field_name == "application_info":
                if (error_type == "value_error" and "too long" in error_msg) or \
                   (error_type == "string_too_long"):
                    error_found_max = True
                    break
            elif "too_long" in error_type:
                error_found_max = True
                break
    assert error_found_max, f"Error detail for {field_name} (max_length violation) not found: {data_too_long['detail']}"

    if min_length is not None and min_length > 0:
        job_data_too_short = base_job_data.copy() # Use copy for modification
        value_too_short = "a" * (min_length - 1) if min_length > 1 else ""
        job_data_too_short[field_name] = value_too_short

        response_too_short = client.post("/api/jobs/", json=job_data_too_short)
        assert response_too_short.status_code == 422, f"Expected 422 for {field_name} below min_length. Response: {response_too_short.text}"
        data_too_short = response_too_short.json()
        assert "detail" in data_too_short
        error_found_min = False
        for error in data_too_short["detail"]:
            if field_name in error.get("loc", []):
                error_type = error.get("type", "")
                if field_name == "application_info":
                    if error_type == "value_error" or error_type == "url_parsing":
                        error_found_min = True
                        break
                    elif "too_short" in error_type:
                        error_found_min = True
                        break
                elif "too_short" in error_type:
                    error_found_min = True
                    break
        assert error_found_min, f"Error detail for {field_name} (min_length violation) not found: {data_too_short['detail']}"

def test_create_job_tags_limit_count(client: TestClient, sample_job_payload_factory):
    """
    Test creating a job fails with 422 if more than 10 tags are provided.
    PRD 6.3: Tags list should not exceed 10 items.
    """
    payload = sample_job_payload_factory()
    payload["tags"] = [f"tag{i}" for i in range(11)]

    response = client.post("/api/jobs/", json=payload)

    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data
    error_found = False
    for error in data["detail"]:
        if error.get("loc") == ["body", "tags"] and "too_long" in error.get("type", ""):
            if "list should have at most 10 items" in error.get("msg", "").lower() or \
               "ensure this value has at most 10 items" in error.get("msg", "").lower():
                error_found = True
                break
            elif "too_long" in error.get("type", ""):
                 error_found = True
                 break
    assert error_found, f"Validation error for tags count limit not found: {data['detail']}"

def test_create_job_tags_limit_length(client: TestClient, sample_job_payload_factory):
    """
    Test creating a job fails with 422 if any tag exceeds 25 characters.
    PRD 6.3: Each tag string length should not exceed 25 characters.
    """
    payload = sample_job_payload_factory()
    long_tag = "a" * 26
    payload["tags"] = ["validtag", long_tag, "anothervalid"]

    response = client.post("/api/jobs/", json=payload)

    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data
    error_found = False
    for error in data["detail"]:
        # This assumes your schema enforces max_length on individual tag strings.
        # If it's a custom validator, the loc might just be ['body', 'tags']
        # and type 'value_error' with a specific message.
        error_loc = error.get("loc", [])
        error_type = error.get("type", "")
        error_msg = error.get("msg", "").lower()

        # Check for Pydantic's built-in string_too_long for list items
        if len(error_loc) == 3 and error_loc[:2] == ["body", "tags"] and isinstance(error_loc[2], int) and "string_too_long" in error_type:
            error_found = True
            break
        # Check for a custom validator on the 'tags' field itself raising a ValueError
        elif error_loc == ["body", "tags"] and "value_error" in error_type and \
             ("tag" in error_msg and "25 characters" in error_msg): # Check for specific message parts
             error_found = True
             break
    assert error_found, f"Validation error for tag length limit not found: {data['detail']}"

def test_create_job_tags_invalid_chars(client: TestClient, sample_job_payload_factory):
    """
    Test creating a job fails with 422 if any tag contains non-alphanumeric characters.
    PRD 6.3: Each tag must be alphanumeric.
    """
    payload = sample_job_payload_factory()
    payload["tags"] = ["validTag1", "invalid tag", "valid2"] # "invalid tag" has a space

    response = client.post("/api/jobs/", json=payload)

    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data
    error_found = False
    for error in data["detail"]:
        error_loc = error.get("loc", [])
        error_type = error.get("type", "")
        error_msg = error.get("msg", "").lower()

        # Expecting a value_error from a custom validator or Pydantic pattern mismatch
        # The location might point to the specific tag or the 'tags' field generally
        if error_loc[:2] == ["body", "tags"]: # Covers loc like ['body', 'tags'] or ['body', 'tags', 1]
            if "value_error" in error_type or "string_pattern_mismatch" in error_type:
                # Check for a message indicating alphanumeric or pattern violation
                if "alphanumeric" in error_msg or "pattern" in error_msg or "must be alphanumeric" in error_msg:
                    error_found = True
                    break
    assert error_found, f"Validation error for non-alphanumeric tag not found or message incorrect: {data['detail']}"

def test_create_job_salary_min_greater_than_max(client: TestClient, sample_job_payload_factory):
    """
    Test creating a job fails with 422 if salary_min > salary_max.
    PRD 6.3: salary_min must be less than or equal to salary_max if both are provided.
    """
    payload = sample_job_payload_factory(
        salary_min=100000,
        salary_max=80000  # min > max
    )

    response = client.post("/api/jobs/", json=payload)

    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data
    error_found = False
    for error in data["detail"]:
        error_msg = error.get("msg", "").lower()
        error_loc = error.get("loc")
        error_type = error.get("type")

        # Check for the specific error message, type, and location related to salary range
        # Based on observed error: {'type': 'value_error', 'loc': ['body', 'salary_max'], 'msg': 'Value error, Maximum salary cannot be less than minimum salary.'}
        # For model_validator, loc is often just ['body']
        expected_msg_part = "maximum salary cannot be less than minimum salary"
        if error_type == "value_error" and \
           error_loc == ['body'] and \
           expected_msg_part in error_msg:
            error_found = True
            break
        # You could also keep a check for a more generic custom type if planned
        # elif error_type == "value_error.salaryrange":
        #     error_found = True
        #     break
    assert error_found, f"Validation error for salary_min > salary_max not found or message incorrect: {data['detail']}"


def test_create_job_salary_currency_defaulted_if_salary_provided(client: TestClient, sample_job_payload_factory): # Renamed for clarity
    """
    Test salary_currency defaults to "USD" if salary is provided but currency is not.
    Implicitly covers PRD 6.3 by ensuring currency is always present with salary.
    """
    scenarios = [
        # Salary min and max, no currency - ensure valid range
        sample_job_payload_factory(salary_min=50000, salary_max=70000, salary_currency=None),
        # Only salary_min, no currency
        sample_job_payload_factory(salary_min=50000, salary_max=None, salary_currency=None), # Explicitly set salary_max to None or ensure factory handles it
        # Only salary_max, no currency
        sample_job_payload_factory(salary_min=None, salary_max=70000, salary_currency=None)  # Explicitly set salary_min to None
    ]

    for payload_args in scenarios:
        # Construct payload from args to ensure None is handled correctly by factory or direct construction
        payload = sample_job_payload_factory(**payload_args)

        # Ensure salary_currency is truly absent if factory might still include it as None
        if "salary_currency" in payload and payload["salary_currency"] is None:
            del payload["salary_currency"]

        response = client.post("/api/jobs/", json=payload)

        assert response.status_code == 201, f"Payload: {payload}, Response: {response.text}"
        data = response.json()
        assert data.get("salary_currency") == "USD", \
            f"Expected salary_currency to default to 'USD'. Payload: {payload}, Response: {data}"

    # Test case: If currency IS provided, it should be respected
    # Ensure valid salary range if both min/max are provided by factory by default
    payload_with_eur_args = {"salary_min": 60000, "salary_max": 80000, "salary_currency": "EUR"}
    payload_with_eur = sample_job_payload_factory(**payload_with_eur_args)
    response_eur = client.post("/api/jobs/", json=payload_with_eur)
    assert response_eur.status_code == 201, f"Payload: {payload_with_eur}, Response: {response_eur.text}"
    data_eur = response_eur.json()
    assert data_eur.get("salary_currency") == "EUR", "Provided currency 'EUR' was not respected."

    # Test case: If NO salary is provided, currency should be None
    payload_no_salary_args = {"salary_min": None, "salary_max": None, "salary_currency": None}
    payload_no_salary = sample_job_payload_factory(**payload_no_salary_args)
    # Ensure keys are truly absent if factory might include them as None
    if "salary_min" in payload_no_salary and payload_no_salary["salary_min"] is None: del payload_no_salary["salary_min"]
    if "salary_max" in payload_no_salary and payload_no_salary["salary_max"] is None: del payload_no_salary["salary_max"]
    if "salary_currency" in payload_no_salary and payload_no_salary["salary_currency"] is None: del payload_no_salary["salary_currency"]
    
    response_no_salary = client.post("/api/jobs/", json=payload_no_salary)
    assert response_no_salary.status_code == 201, f"Payload: {payload_no_salary}, Response: {response_no_salary.text}"
    data_no_salary = response_no_salary.json()
    assert data_no_salary.get("salary_currency") is None, \
        f"Currency should be None when no salary is provided. Response: {data_no_salary}"

    payload_no_salary_with_currency_args = {"salary_min": None, "salary_max": None, "salary_currency": "CAD"}
    payload_no_salary_with_currency = sample_job_payload_factory(**payload_no_salary_with_currency_args)
    # Ensure keys are truly absent
    if "salary_min" in payload_no_salary_with_currency and payload_no_salary_with_currency["salary_min"] is None: del payload_no_salary_with_currency["salary_min"]
    if "salary_max" in payload_no_salary_with_currency and payload_no_salary_with_currency["salary_max"] is None: del payload_no_salary_with_currency["salary_max"]

    response_no_salary_curr = client.post("/api/jobs/", json=payload_no_salary_with_currency)
    assert response_no_salary_curr.status_code == 201, f"Payload: {payload_no_salary_with_currency}, Response: {response_no_salary_curr.text}" # Schema now makes currency None if no salary
    data_no_salary_curr = response_no_salary_curr.json()
    assert data_no_salary_curr.get("salary_currency") is None, \
        f"Currency should be None when no salary is provided, even if input. Response: {data_no_salary_curr}"


def test_create_job_poster_username_generated_if_not_provided(client: TestClient, sample_job_payload_factory, db_session: Session): # RENAMED for clarity
    """
    Test poster_username is generated if not provided during job creation.
    PRD 5.2 & 6.3: If poster_username is not provided, backend assigns a random name.
    """
    payload = sample_job_payload_factory()
    # Ensure poster_username is not in the payload to test the default mechanism
    if "poster_username" in payload:
        del payload["poster_username"] 

    response = client.post("/api/jobs/", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()
    
    assert "poster_username" in data, "poster_username field missing in response"
    generated_username = data["poster_username"]
    assert generated_username is not None, "Generated poster_username should not be None"
    assert isinstance(generated_username, str), "Generated poster_username should be a string"
    assert len(generated_username.strip()) > 0, "Generated poster_username should not be empty or just whitespace"
    
    # Optional: More specific check if the generated name contains a space (suggesting "Adjective Noun")
    # This assumes your generate_unique_poster_username always creates names with a space.
    assert " " in generated_username, f"Generated username '{generated_username}' does not look like 'Adjective Noun'"

    # Optional: Verify in DB as well
    # from models import Job as JobModel # Ensure this import is at the top if used
    # db_job = db_session.query(JobModel).filter(JobModel.id == data["id"]).first()
    # assert db_job is not None
    # assert db_job.poster_username == generated_username

def test_create_job_fails_when_max_row_limit_reached(client: TestClient, sample_job_payload_factory, db_session: Session):
    """
    Test that creating a job fails with a 503 error when the MAX_JOB_POSTINGS_LIMIT is reached.
    """
    # Ensure the database is clean for this specific test if not already handled by fixtures
    # (Pytest-SQLAlchemy usually handles this with transaction rollbacks per test)

    # Create jobs up to the limit
    for i in range(MAX_JOB_POSTINGS_LIMIT):
        # Ensure each payload is somewhat unique if necessary, e.g., by title,
        # to avoid accidental unique constraint issues if the factory isn't perfectly unique
        # and the test runs very fast. For this test, basic uniqueness in title should suffice.
        payload = sample_job_payload_factory(title=f"Test Job {i+1} to reach limit")
        response = client.post("/api/jobs/", json=payload)
        assert response.status_code == 201, \
            f"Failed to create job {i+1}/{MAX_JOB_POSTINGS_LIMIT}. Response: {response.text}"

    # Attempt to create one more job, which should exceed the limit
    overflow_payload = sample_job_payload_factory(title="Overflow Job")
    response_overflow = client.post("/api/jobs/", json=overflow_payload)

    assert response_overflow.status_code == 503, \
        f"Expected 503 status code when exceeding row limit, got {response_overflow.status_code}. Response: {response_overflow.text}"
    
    data = response_overflow.json()
    assert "detail" in data, "Error response should contain a 'detail' field."
    expected_error_message = f"Cannot create new job. The maximum limit of {MAX_JOB_POSTINGS_LIMIT} job postings has been reached."
    assert data["detail"] == expected_error_message, \
        f"Unexpected error message. Expected: '{expected_error_message}', Got: '{data['detail']}'"

    # Verify that the total number of jobs in the database is indeed MAX_JOB_POSTINGS_LIMIT
    # This requires importing your Job model
    from models import Job as JobModel # Ensure this import is at the top of the file or within the test
    job_count_in_db = db_session.query(JobModel).count()
    assert job_count_in_db == MAX_JOB_POSTINGS_LIMIT, \
        f"Expected {MAX_JOB_POSTINGS_LIMIT} jobs in DB, found {job_count_in_db}"
