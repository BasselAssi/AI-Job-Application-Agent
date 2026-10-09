from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st

from analysis import JobAnalysisError, analyze_cv_match, analyze_job_posting
from job_fetcher import JobFetchError, fetch_job_posting
from models import CVMatchReport, JobRequirements


PROFILE_FILE = Path(__file__).parent / "profile.txt"


def render_job_requirements(requirements: JobRequirements) -> None:
    """Display validated model output as reviewable job-posting fields."""
    st.subheader("Extracted job requirements")
    st.warning(
        "AI-generated extraction—review it against the original posting before "
        "using it."
    )
    st.markdown(f"**Job title:** {requirements.title or 'Not stated'}")

    sections = (
        ("Responsibilities", requirements.responsibilities),
        ("Required skills", requirements.required_skills),
        ("Preferred skills", requirements.preferred_skills),
        ("Technologies", requirements.technologies),
        ("Experience requirements", requirements.experience_requirements),
    )
    for heading, items in sections:
        st.markdown(f"**{heading}**")
        if items:
            for item in items:
                st.markdown(f"- {item}")
        else:
            st.write("Not identified in the posting.")


def render_cv_match_report(report: CVMatchReport) -> None:
    """Display the evidence-based CV-to-job comparison."""
    st.subheader("CV match assessment")
    st.warning(
        "AI-generated assessment—verify each point against the original job "
        "posting and your experience."
    )
    st.markdown(f"**Overall fit: {report.fit_level}**")
    st.write(report.summary)

    sections = (
        ("Evidence-backed strengths", report.strengths),
        ("Requirements without clear CV evidence", report.gaps),
        ("Suggested next steps", report.suggested_actions),
    )
    for heading, items in sections:
        st.markdown(f"**{heading}**")
        if items:
            for item in items:
                st.markdown(f"- {item}")
        else:
            st.write("None identified.")


def fetch_posting_from_form() -> None:
    """Fetch the URL from the form before Streamlit reruns the page."""
    job_url = st.session_state.get("job_url", "").strip()
    st.session_state["fetch_error"] = ""
    st.session_state["fetch_notice"] = ""

    if not job_url:
        st.session_state["fetch_error"] = "Enter a job posting URL first."
        return

    try:
        job_text = fetch_job_posting(job_url)
    except JobFetchError as error:
        st.session_state["fetch_error"] = str(error)
        return

    st.session_state["job_description"] = job_text
    st.session_state["fetch_notice"] = (
        "Job page text was fetched. Review and edit it below before continuing."
    )


def is_http_url(value: str) -> bool:
    """Return whether the value is an absolute HTTP or HTTPS URL."""
    try:
        parsed_url = urlsplit(value.strip())
    except ValueError:
        return False

    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.hostname)


def load_profile() -> str:
    """Load the optional local profile file without hiding read errors."""
    try:
        return PROFILE_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as error:
        st.error(f"Could not read {PROFILE_FILE.name}: {error}")
        return ""


st.set_page_config(
    page_title="Job Application Assistant",
    page_icon="🧭",
    layout="centered",
)

st.title("My Job Application Assistant")
st.write(
    "Fetch a public job page or paste its description, review the text, then "
    "extract its requirements or assess how well your CV/profile matches."
)

saved_profile = load_profile()
if not saved_profile:
    st.info(
        "To preload your profile, create a local profile.txt file using "
        "profile.example.txt as a starting point. You can also paste your "
        "profile below."
    )

with st.form("job_application_inputs"):
    st.subheader("Job posting")
    job_url = st.text_input(
        "Job posting URL",
        placeholder="https://example.com/jobs/123",
        help="Enter a public job posting URL, then choose Fetch posting.",
        key="job_url",
    )
    st.form_submit_button("Fetch posting", on_click=fetch_posting_from_form)
    job_description = st.text_area(
        "Job description (optional if a URL is provided)",
        height=180,
        placeholder="Paste the job description here if you do not have a URL.",
        key="job_description",
    )
    preferred_location = st.text_input(
        "Preferred location (optional)",
        placeholder="e.g. Montreal, QC or Remote",
    )

    st.subheader("Your profile")
    profile_text = st.text_area(
        "CV or profile text",
        height=220,
        placeholder="Paste relevant experience, skills, education, and certifications.",
        value=saved_profile,
        help="Preloaded from profile.txt when available. Changes in this form are not saved to the file.",
    )

    submitted = st.form_submit_button("Review inputs")
    analyze_submitted = st.form_submit_button(
        "Analyze job requirements",
        type="primary",
    )
    match_submitted = st.form_submit_button("Assess CV match")
    st.caption(
        "Assess CV match sends both the job description and CV/profile text to "
        "your configured Gemini API. Use it only if you’re comfortable sharing "
        "that information with the API provider."
    )

if st.session_state.get("fetch_error"):
    st.error(st.session_state["fetch_error"])
if st.session_state.get("fetch_notice"):
    st.success(st.session_state["fetch_notice"])

if analyze_submitted:
    try:
        with st.spinner("Analyzing the job posting with Gemini..."):
            requirements = analyze_job_posting(job_description)
        st.session_state["job_requirements"] = requirements
        st.session_state["analyzed_job_text"] = job_description
        st.session_state.pop("analysis_error", None)
    except JobAnalysisError as error:
        st.session_state["analysis_error"] = str(error)

if match_submitted:
    try:
        with st.spinner("Comparing your CV with the job posting..."):
            match_report = analyze_cv_match(job_description, profile_text)
        st.session_state["cv_match_report"] = match_report
        st.session_state["matched_job_text"] = job_description
        st.session_state["matched_cv_text"] = profile_text
        st.session_state.pop("match_error", None)
    except JobAnalysisError as error:
        st.session_state["match_error"] = str(error)

if st.session_state.get("analysis_error"):
    st.error(st.session_state["analysis_error"])

if st.session_state.get("match_error"):
    st.error(st.session_state["match_error"])

saved_requirements = st.session_state.get("job_requirements")
if saved_requirements:
    current_job_text = st.session_state.get("job_description", "")
    analyzed_job_text = st.session_state.get("analyzed_job_text", "")
    if current_job_text == analyzed_job_text:
        render_job_requirements(saved_requirements)
    else:
        st.info("The job text changed. Analyze it again to refresh these results.")

saved_match_report = st.session_state.get("cv_match_report")
if saved_match_report:
    if (
        job_description == st.session_state.get("matched_job_text", "")
        and profile_text == st.session_state.get("matched_cv_text", "")
    ):
        render_cv_match_report(saved_match_report)
    else:
        st.info("The job text or CV/profile changed. Assess the match again.")

if submitted:
    errors = []

    if not profile_text.strip():
        errors.append("Add your CV or profile text.")

    if job_url.strip() and not is_http_url(job_url):
        errors.append("The job posting URL must start with http:// or https://.")
    elif not job_url.strip() and not job_description.strip():
        errors.append("Provide a job posting URL or paste the job description.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        st.success("Your inputs are ready for the next step.")

        if job_url.strip() and job_description.strip():
            job_source = "URL and job description text"
        elif job_url.strip():
            job_source = "URL"
        else:
            job_source = "Pasted description"
        st.write(f"**Job posting provided by:** {job_source}")
        if preferred_location.strip():
            st.write(f"**Preferred location:** {preferred_location.strip()}")
        else:
            st.write("**Preferred location:** Not provided")
        st.write(f"**Profile text:** {len(profile_text.strip())} characters")
        if job_description.strip():
            st.write(f"**Job description text:** {len(job_description.strip())} characters")

        st.info(
            "The posting text is only fetched when you choose Fetch posting. "
            "Choosing Analyze job requirements sends only the job text to your "
            "configured Gemini API. Choosing Assess CV match sends both the "
            "posting and CV/profile text. This app does not save your profile "
            "or submit an application."
        )

st.caption(
    "Learning MVP · Review all future AI-generated content yourself; "
    "this app will not submit applications."
)
