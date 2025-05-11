-- Script to create tables for NextHire on Neon
-- This should be run manually in the Neon SQL editor.

-- Drop table if it exists (optional, for a clean setup during development/testing on Neon)
-- Be cautious with DROP TABLE in a production environment.
-- DROP TABLE IF EXISTS jobs;
-- DROP TABLE IF EXISTS alembic_version; -- If you also want to clear Alembic's table from Neon

-- Create the jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Using gen_random_uuid() for default UUID generation in PostgreSQL
    title VARCHAR(100) NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    description TEXT NOT NULL,
    application_info VARCHAR(255) NOT NULL,
    job_type VARCHAR(50),
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10),
    poster_username VARCHAR(50) NOT NULL,
    tags VARCHAR(25)[], -- Array of strings, each up to 25 chars
    modification_code VARCHAR(8) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX ix_jobs_title ON jobs (title);
CREATE INDEX ix_jobs_company_name ON jobs (company_name);
CREATE INDEX ix_jobs_poster_username ON jobs (poster_username);
-- The index on 'id' is automatically created because it's a PRIMARY KEY.
-- The index on 'modification_code' is automatically created because of the UNIQUE constraint.

-- Optional: Add a trigger to automatically update updated_at timestamp
-- This is an alternative to relying on SQLAlchemy's onupdate in the model,
-- ensuring it happens at the DB level regardless of how data is inserted/updated.
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp_jobs
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Note: Alembic also creates an 'alembic_version' table to track migrations.
-- If you are managing the schema entirely manually on Neon, you might not need this table there.
-- However, if you ever plan to point Alembic (even for read-only checks) at Neon,
-- it might look for it. For a fully manual setup, it's not strictly required on Neon.
-- If you do want it:
-- CREATE TABLE alembic_version (
--     version_num VARCHAR(32) NOT NULL,
--     CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
-- );

COMMENT ON TABLE jobs IS 'Stores job postings for the NextHire application';
COMMENT ON COLUMN jobs.id IS 'Unique identifier for the job posting (UUID)';
COMMENT ON COLUMN jobs.title IS 'Job title';
COMMENT ON COLUMN jobs.company_name IS 'Name of the company posting the job';
COMMENT ON COLUMN jobs.location IS 'Job location (e.g., City, State, Remote)';
COMMENT ON COLUMN jobs.description IS 'Full job description';
COMMENT ON COLUMN jobs.application_info IS 'Application link (URL) or email address';
COMMENT ON COLUMN jobs.job_type IS 'Type of job (e.g., Full-time, Part-time)';
COMMENT ON COLUMN jobs.salary_min IS 'Minimum salary offered';
COMMENT ON COLUMN jobs.salary_max IS 'Maximum salary offered';
COMMENT ON COLUMN jobs.salary_currency IS 'Currency for the salary (e.g., USD)';
COMMENT ON COLUMN jobs.poster_username IS 'Username of the person who posted the job';
COMMENT ON COLUMN jobs.tags IS 'Array of tags associated with the job';
COMMENT ON COLUMN jobs.modification_code IS 'Unique 8-character code for editing/deleting the job posting';
COMMENT ON COLUMN jobs.created_at IS 'Timestamp of when the job posting was created';
COMMENT ON COLUMN jobs.updated_at IS 'Timestamp of when the job posting was last updated';