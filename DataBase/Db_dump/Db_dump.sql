DROP TRIGGER IF EXISTS set_timestamp_users ON public.users;
DROP TRIGGER IF EXISTS set_timestamp_jobs ON public.jobs;
DROP TRIGGER IF EXISTS set_timestamp_activities ON public.activities;
DROP TRIGGER IF EXISTS set_timestamp_applications ON public.applications;
DROP TRIGGER IF EXISTS email_check ON public.users;
DROP TRIGGER IF EXISTS phone_check ON public.users;

DROP TABLE IF EXISTS public.applications;
DROP TABLE IF EXISTS public.faq;
DROP TABLE IF EXISTS public.company_contacts;
DROP TABLE IF EXISTS public.hr_contacts;
DROP TABLE IF EXISTS public.activities;
DROP TABLE IF EXISTS public.jobs;
DROP TABLE IF EXISTS public.users;

DROP FUNCTION IF EXISTS public.check_email_format();
DROP FUNCTION IF EXISTS public.check_phone_format();
DROP FUNCTION IF EXISTS public.update_updated_at_column();

DROP TYPE IF EXISTS public.application_status;
DROP TYPE IF EXISTS public.job_type;

CREATE TYPE public.job_type AS ENUM ('internship', 'vacancy');
CREATE TYPE public.application_status AS ENUM ('pending', 'under_review', 'interview', 'offer', 'hired', 'rejected', 'withdrawn');

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE FUNCTION public.check_email_format() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.email IS NOT NULL AND NEW.email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN
        RAISE EXCEPTION 'Invalid email format: %', NEW.email;
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION public.check_phone_format() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.phone IS NOT NULL AND NEW.phone !~ '^\+?[0-9]{10,15}$' THEN
        RAISE EXCEPTION 'Invalid phone format: %', NEW.phone;
    END IF;
    RETURN NEW;
END;
$$;


-- Table Creation

CREATE TABLE public.users (
    id BIGINT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    gender VARCHAR(10),
    birth_date DATE,
    city VARCHAR(100),
    education TEXT,
    work_experience TEXT,
    skills TEXT,
    desired_salary NUMERIC(12, 2),
    desired_employment VARCHAR(100),
    relocation_readiness BOOLEAN DEFAULT false,
    about_me TEXT,
    photo BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON COLUMN public.users.id IS 'Primary key, likely Telegram User ID';
COMMENT ON COLUMN public.users.photo IS 'Binary photo data. Consider storing a URL/path instead.';

CREATE TABLE public.jobs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type public.job_type NOT NULL,
    required_education TEXT,
    required_experience TEXT,
    required_skills TEXT,
    additional_skills TEXT,
    employment_type VARCHAR(100),
    work_schedule VARCHAR(100),
    workday_start TIME,
    workday_end TIME,
    salary NUMERIC(12, 2),
    additional_info TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE public.jobs IS 'Stores details about internships and job vacancies';

CREATE TABLE public.activities (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    address TEXT,
    target_audience TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT activities_time_check CHECK (end_time >= start_time)
);
COMMENT ON TABLE public.activities IS 'Stores details about company events or activities';

CREATE TABLE public.applications (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    job_id INTEGER,
    activity_id INTEGER,
    status public.application_status NOT NULL DEFAULT 'pending',
    hr_comment TEXT,
    application_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES public.users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_job
        FOREIGN KEY(job_id)
        REFERENCES public.jobs(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_activity
        FOREIGN KEY(activity_id)
        REFERENCES public.activities(id)
        ON DELETE CASCADE,

    CONSTRAINT application_target_check
        CHECK (
            (job_id IS NOT NULL AND activity_id IS NULL)
            OR
            (job_id IS NULL AND activity_id IS NOT NULL)
        )
);
COMMENT ON TABLE public.applications IS 'User applications for either jobs/internships OR activities';
COMMENT ON COLUMN public.applications.status IS 'Current status of the application';
COMMENT ON CONSTRAINT application_target_check ON public.applications IS 'Ensures an application is linked to EITHER a job OR an activity, not both or neither.';

CREATE TABLE public.hr_contacts (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL
);
COMMENT ON TABLE public.hr_contacts IS 'Contact information for HR personnel';

CREATE TABLE public.company_contacts (
    id SERIAL PRIMARY KEY,
    department VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL
);
COMMENT ON TABLE public.company_contacts IS 'General company contact information, possibly departmental';

CREATE TABLE public.faq (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0
);
COMMENT ON TABLE public.faq IS 'Frequently Asked Questions and their answers';
COMMENT ON COLUMN public.faq.display_order IS 'Order in which to display FAQs, lower numbers first';


-- Create Triggers

CREATE TRIGGER set_timestamp_users
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE PROCEDURE public.update_updated_at_column();

CREATE TRIGGER set_timestamp_jobs
BEFORE UPDATE ON public.jobs
FOR EACH ROW
EXECUTE PROCEDURE public.update_updated_at_column();

CREATE TRIGGER set_timestamp_activities
BEFORE UPDATE ON public.activities
FOR EACH ROW
EXECUTE PROCEDURE public.update_updated_at_column();

CREATE TRIGGER set_timestamp_applications
BEFORE UPDATE ON public.applications
FOR EACH ROW
EXECUTE PROCEDURE public.update_updated_at_column();

CREATE TRIGGER email_check
BEFORE INSERT OR UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.check_email_format();

CREATE TRIGGER phone_check
BEFORE INSERT OR UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.check_phone_format();

-- Create Indexes for performance

CREATE INDEX idx_applications_user_id ON public.applications(user_id);
CREATE INDEX idx_applications_job_id ON public.applications(job_id);
CREATE INDEX idx_applications_activity_id ON public.applications(activity_id);
CREATE INDEX idx_applications_status ON public.applications(status);
CREATE INDEX idx_jobs_type ON public.jobs(type);
CREATE INDEX idx_jobs_is_active ON public.jobs(is_active);
CREATE INDEX idx_activities_is_active ON public.activities(is_active);
CREATE INDEX idx_faq_display_order ON public.faq(display_order);
CREATE INDEX idx_users_city ON public.users(city);

SELECT 'Database schema created successfully.' as status;