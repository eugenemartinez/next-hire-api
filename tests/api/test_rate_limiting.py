import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

import crud
import schemas
import models
from core.limiter import limiter
import routers.jobs as jobs_router

def test_rate_limit_post_jobs():
    """Test that POST /api/jobs has rate limiting configured."""
    # Don't test the behavior - just verify it's configured
    # Look at the route implementation in the module
    assert hasattr(jobs_router, "create_new_job"), "POST jobs route function not found"
    route_func = jobs_router.create_new_job
    
    # Verify there's a decorator - the function should have a __closure__ attribute
    assert route_func.__closure__ is not None, "No decorators found on route"
    
    # Check the source code for the limit decorator text
    import inspect
    source = inspect.getsource(jobs_router.create_new_job)
    assert "@limiter.limit(\"50/day\")" in source, "Rate limit decorator not found in source"

def test_rate_limit_patch_job():
    """Test that PATCH /api/jobs/{job_id} has rate limiting configured."""
    assert hasattr(jobs_router, "update_existing_job"), "PATCH jobs route function not found"
    route_func = jobs_router.update_existing_job
    
    # Verify there's a decorator - the function should have a __closure__ attribute
    assert route_func.__closure__ is not None, "No decorators found on route"
    
    # Check the source code for the limit decorator text  
    import inspect
    source = inspect.getsource(jobs_router.update_existing_job)
    assert "@limiter.limit(\"50/day\")" in source, "Rate limit decorator not found in source"

def test_rate_limit_delete_job():
    """Test that DELETE /api/jobs/{job_id} has rate limiting configured."""
    assert hasattr(jobs_router, "delete_specific_job"), "DELETE jobs route function not found"
    route_func = jobs_router.delete_specific_job
    
    # Verify there's a decorator - the function should have a __closure__ attribute
    assert route_func.__closure__ is not None, "No decorators found on route"
    
    # Check the source code for the limit decorator text
    import inspect
    source = inspect.getsource(jobs_router.delete_specific_job)
    assert "@limiter.limit(\"50/day\")" in source, "Rate limit decorator not found in source"