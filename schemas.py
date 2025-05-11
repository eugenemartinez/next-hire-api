from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator, model_validator, UUID4, ValidationInfo # Ensure model_validator is imported
from typing import List, Optional, Union, Any 
from datetime import datetime
import re 
from enum import Enum # Ensure Enum is imported

# Regex for basic alphanumeric validation (allows spaces in between words for some fields)
# For tags and username, we might want stricter (no spaces)
ALPHANUMERIC_PATTERN = r"^[a-zA-Z0-9 ]+$" # Example, not currently used for tags/username directly

# Updated TAG_ALPHANUMERIC_PATTERN_COMPILED for more common tag characters
# Allows alphanumeric, hash, plus, period, slash, hyphen.
# Hyphen must be at the end of the character set [] or escaped if in the middle.
TAG_ALPHANUMERIC_PATTERN_COMPILED = re.compile(r"^[a-zA-Z0-9#+./-]+$")

# USERNAME_ALPHANUMERIC_PATTERN remains a string as it's used by Pydantic's Field(pattern=...)
USERNAME_ALPHANUMERIC_PATTERN = r"^[a-zA-Z0-9_]+$"
USERNAME_WITH_SPACES_PATTERN = r"^[a-zA-Z0-9_ ]+$" # Added space

# --- Enum for Job Type ---
class JobType(str, Enum):
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"

# --- Enum for Popular Currencies ---
class PopularCurrency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    # Add more as needed

# --- Base Schemas ---
class JobBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Job title")
    company_name: str = Field(..., min_length=1, max_length=100, description="Name of the company")
    location: Optional[str] = Field(None, max_length=100, description="Job location (e.g., 'City, State', 'Remote')")
    description: str = Field(..., min_length=1, max_length=5000, description="Full job description")
    application_info: Union[EmailStr, HttpUrl] = Field(
        ..., 
        max_length=255,
        min_length=1,
        description="Application link (URL) or email address"
    )
    job_type: Optional[JobType] = Field(None, description="E.g., 'Full-time', 'Part-time', 'Contract'")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary")
    salary_currency: Optional[PopularCurrency] = Field(None, description="Popular currency code") # Changed from str to PopularCurrency
    
    poster_username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=USERNAME_WITH_SPACES_PATTERN, # Use the new pattern
        description="Username of the job poster (alphanumeric, underscores, spaces allowed)" # Update description
    )
    tags: Optional[List[str]] = Field(
        default_factory=list, # CHANGED FROM None to default_factory=list
        max_length=10,
        description="List of tags associated with the job (max 10 tags, common characters allowed)"
    )

    @field_validator('poster_username', mode='before')
    @classmethod
    def empty_username_to_none(cls, v: Any) -> Optional[str]:
        if isinstance(v, str) and v == "":
            return None
        return v

    @field_validator('job_type', mode='before')
    @classmethod
    def job_type_to_enum_value(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            # Convert string from DB (e.g., "Full-time") to lowercase ("full-time")
            # Pydantic will then validate this lowercase string against the JobType enum values.
            return v.lower()
        # If it's already an enum instance (e.g., from a request body) or None, pass it through.
        # If v is already a JobType enum instance, this will also correctly pass it.
        return v

    @field_validator('tags', mode='before')
    @classmethod
    def validate_tags_content(cls, v: Optional[List[str]]) -> List[str]: # Consider changing return type hint to List[str]
        if v is None:
            return [] # If input is None, return empty list as per PRD default
        if not isinstance(v, list):
            # This case might be less likely if default_factory=list is used,
            # but good for robustness if data comes from other sources.
            raise ValueError("Tags must be a list of strings.")
        
        validated_tags = []
        for tag_item in v:
            if not isinstance(tag_item, str):
                raise ValueError("Each tag must be a string.")
            
            stripped_tag = tag_item.strip()
            if not stripped_tag:
                continue # Skip empty tags

            # Assuming MAX_TAG_LENGTH is around 25-50 for individual tags
            # Let's define it for clarity if not already globally defined
            MAX_TAG_LENGTH = 25 # PRD: each tag max 25 chars
            if not (1 <= len(stripped_tag) <= MAX_TAG_LENGTH): # Ensure individual tag length is also checked
                raise ValueError(f"Tag '{stripped_tag[:30]}...' must be between 1 and {MAX_TAG_LENGTH} characters long.")
            
            if not TAG_ALPHANUMERIC_PATTERN_COMPILED.match(stripped_tag):
                raise ValueError(
                    f"Tag '{stripped_tag}' contains invalid characters. "
                    f"Allowed: alphanumeric, and # + . / -"
                )
            validated_tags.append(stripped_tag.lower()) # Convert to lowercase for consistency
        
        unique_tags = list(set(validated_tags)) # Remove duplicates
        # The Field definition for 'tags' already has max_length=10 for the list itself.
        # Pydantic will enforce this after this 'before' validator.
        return unique_tags # CHANGED HERE: Directly return unique_tags. If it's empty, it will be []

    @model_validator(mode='after')
    def validate_and_normalize_salary_info(self) -> 'JobBase':
        salary_provided = self.salary_min is not None or self.salary_max is not None

        # Rule 1: salary_max must be >= salary_min if both are provided
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("Maximum salary cannot be less than minimum salary.")

        # Rule 2: Handle salary_currency
        if salary_provided:
            if self.salary_currency is None:
                self.salary_currency = PopularCurrency.USD  # Default to USD Enum member
            # Pydantic will validate if the provided string is a valid PopularCurrency member
        elif self.salary_currency is not None:
            self.salary_currency = None
        
        return self

# --- Schema for Job Creation ---
class JobCreate(JobBase):
    # poster_username is already optional in JobBase.
    # If not provided, the backend will generate one.
    pass

# --- Schema for Job Update ---
# All fields are optional for PATCH operations
class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    company_name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    application_info: Optional[Union[EmailStr, HttpUrl]] = None
    job_type: Optional[JobType] = Field(None, description="E.g., 'Full-time', 'Part-time', 'Contract'") # Use the JobType enum
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=10)
    # poster_username is typically not updatable by the user after creation.
    tags: Optional[List[str]] = Field(None, max_length=10) # CHANGED max_items to max_length

    # Re-apply validators if needed, or ensure they are inherited/handled correctly
    # For JobUpdate, if a field is provided, it should still meet validation criteria.
    # Pydantic usually handles this well if fields are re-declared with constraints.
    @field_validator('tags', mode='before')
    @classmethod
    def validate_update_tags_content(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        # Same validation as in JobBase, but applied to optional field
        if v is None:
            return None
        # Delegate to JobBase's validator or repeat logic
        return JobBase.validate_tags_content(v)

    @field_validator('salary_max')
    @classmethod
    def validate_update_salary_range(cls, salary_max: Optional[int], values) -> Optional[int]:
        # This needs careful handling for partial updates.
        # If only salary_max is provided, we can't compare with salary_min from the payload.
        # This kind of validation is better done in the service layer where we have the existing record.
        # For now, we'll keep basic individual field validation.
        # The service layer will handle cross-field validation with existing data.
        return salary_max


# --- Schema for Reading Job Data (Public View) ---
class Job(JobBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True} # UPDATED

# --- Schema for Job Data including Modification Code (e.g., for response after creation) ---
class JobWithModificationCode(Job):
    modification_code: str = Field(..., min_length=8, max_length=8)

    model_config = {"from_attributes": True} # UPDATED

# --- Schema for a list of jobs with pagination metadata ---
class JobListResponse(BaseModel):
    jobs: List[Job] # List of public Job views
    limit: int
    skip: int
    total: int # Could be total in the current response, or total in DB matching criteria

    model_config = {"from_attributes": True} # UPDATED

# --- Schema for the response after deleting a job ---
class JobDeleteResponse(BaseModel):
    message: str
    job_id: UUID4

# --- Schemas for Auxiliary Endpoints ---
class JobIdsList(BaseModel):
    job_ids: List[UUID4] = Field(..., description="A list of job UUIDs to retrieve.")

class JobModificationCodePayload(BaseModel):
    modification_code: str = Field(..., min_length=8, max_length=8, description="The 8-character modification code to verify.")

class JobVerificationResponse(BaseModel):
    verified: bool
    error: Optional[str] = None