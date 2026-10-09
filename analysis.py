from ai_client import (
    AIConfigurationError,
    AIRequestError,
    assess_cv_match as request_cv_match,
    extract_job_requirements,
)
from models import CVMatchReport, JobRequirements


class JobAnalysisError(Exception):
    """A user-facing error while analyzing a job posting."""


def analyze_job_posting(job_text: str) -> JobRequirements:
    """Validate input and return structured requirements from Gemini."""
    if not job_text.strip():
        raise JobAnalysisError("Add or fetch a job description before analyzing it.")

    try:
        return extract_job_requirements(job_text.strip())
    except (AIConfigurationError, AIRequestError) as error:
        raise JobAnalysisError(str(error)) from error


def analyze_cv_match(job_text: str, cv_text: str) -> CVMatchReport:
    """Validate inputs and return a CV-to-job match assessment."""
    if not job_text.strip():
        raise JobAnalysisError("Add or fetch a job description before assessing fit.")
    if not cv_text.strip():
        raise JobAnalysisError("Add your CV or profile before assessing fit.")

    try:
        return request_cv_match(job_text.strip(), cv_text.strip())
    except (AIConfigurationError, AIRequestError) as error:
        raise JobAnalysisError(str(error)) from error
