import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, func, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from core.database import Base # Import Base from our database setup
from datetime import datetime

class Job(Base):
    __tablename__ = "jobs"

    # Core Fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(100), nullable=False, index=True)
    company_name = Column(String(100), nullable=False, index=True)
    location = Column(String(100), nullable=True)
    description = Column(Text, nullable=False) # Text for potentially long descriptions
    application_info = Column(String(255), nullable=False) # Store as string, validation at schema level
    job_type = Column(String(50), nullable=True)

    # Salary Fields
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(10), nullable=True)

    # Poster and Tags
    poster_username = Column(String(50), nullable=False, index=True) # Will be generated if not provided
    tags = Column(ARRAY(String(25)), nullable=True) # Array of strings, max 25 chars per tag

    # Modification Code (not directly exposed in all schemas)
    # This should be a secure, randomly generated string.
    # We'll generate this in the application logic.
    modification_code = Column(String(8), nullable=False, unique=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Optional: A field to mark if the job posting is active/approved, if needed later
    # is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company_name}')>"

    # Example of a hybrid property if we needed to combine salary info, for instance.
    # Not strictly needed based on current schemas but good for illustration.
    @hybrid_property
    def salary_range(self):
        if self.salary_min is not None and self.salary_max is not None:
            return f"{self.salary_min} - {self.salary_max} {self.salary_currency or ''}".strip()
        elif self.salary_min is not None:
            return f"From {self.salary_min} {self.salary_currency or ''}".strip()
        elif self.salary_max is not None:
            return f"Up to {self.salary_max} {self.salary_currency or ''}".strip()
        return None