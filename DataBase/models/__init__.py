from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, EmailStr, model_validator

class JobType(str, Enum):
    INTERNSHIP = 'internship'
    VACANCY = 'vacancy'

class ApplicationStatus(str, Enum):
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    INTERVIEW = 'interview'
    OFFER = 'offer'
    HIRED = 'hired'
    REJECTED = 'rejected'
    WITHDRAWN = 'withdrawn'

class BaseDBModel(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime

class User(BaseModel):
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    city: Optional[str] = None
    education: Optional[str] = None
    work_experience: Optional[str] = None
    skills: Optional[str] = None
    desired_salary: Optional[Decimal] = None
    desired_employment: Optional[str] = None
    relocation_readiness: bool = False
    about_me: Optional[str] = None
    photo: Optional[bytes] = None
    created_at: datetime
    updated_at: datetime

class UserCreate(BaseModel):
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    city: Optional[str] = None
    education: Optional[str] = None
    work_experience: Optional[str] = None
    skills: Optional[str] = None
    desired_salary: Optional[Decimal] = None
    desired_employment: Optional[str] = None
    relocation_readiness: bool = False
    about_me: Optional[str] = None
    photo: Optional[bytes] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    city: Optional[str] = None
    education: Optional[str] = None
    work_experience: Optional[str] = None
    skills: Optional[str] = None
    desired_salary: Optional[Decimal] = None
    desired_employment: Optional[str] = None
    relocation_readiness: Optional[bool] = None
    about_me: Optional[str] = None
    photo: Optional[bytes] = None

class Job(BaseDBModel):
    title: str
    description: Optional[str] = None
    type: JobType
    required_education: Optional[str] = None
    required_experience: Optional[str] = None
    required_skills: Optional[str] = None
    additional_skills: Optional[str] = None
    employment_type: Optional[str] = None
    work_schedule: Optional[str] = None
    workday_start: Optional[time] = None
    workday_end: Optional[time] = None
    salary: Optional[Decimal] = None
    additional_info: Optional[str] = None
    is_active: bool = True

class Activity(BaseDBModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    address: Optional[str] = None
    target_audience: Optional[str] = None
    is_active: bool = True

class Application(BaseDBModel):
    user_id: int
    job_id: Optional[int] = None
    activity_id: Optional[int] = None
    status: ApplicationStatus
    hr_comment: Optional[str] = None
    application_time: datetime

class ApplicationCreate(BaseModel):
    user_id: int
    job_id: Optional[int] = None
    activity_id: Optional[int] = None

    @model_validator(mode='after')
    def check_target(self) -> 'ApplicationCreate':
        if self.job_id is not None and self.activity_id is not None:
            raise ValueError('Application cannot be for both job and activity')
        if self.job_id is None and self.activity_id is None:
            raise ValueError('Application must target a job or an activity')
        return self

class ApplicationWithdraw(BaseModel):
    pass

class FAQ(BaseModel):
    id: int
    question: str
    answer: str
    display_order: int = 0

class HRContact(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str

class CompanyContact(BaseModel):
    id: int
    department: str
    email: EmailStr
    phone: str

class ContentRepoData(BaseModel):
    faqs: List[FAQ] = []
    hr_contacts: List[HRContact] = []
    company_contacts: List[CompanyContact] = []

class ReminderType(str, Enum):
    H24 = "24h"

class ActivityReminder(BaseDBModel):
    user_id: int
    activity_id: int
    reminder_type: ReminderType
    sent_at: datetime
