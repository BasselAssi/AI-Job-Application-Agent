import unittest
from unittest.mock import patch

from ai_client import AIConfigurationError
from analysis import JobAnalysisError, analyze_cv_match, analyze_job_posting
from models import CVMatchReport, JobRequirements


class AnalyzeJobPostingTests(unittest.TestCase):
    def test_rejects_blank_posting_without_calling_model(self):
        with patch("analysis.extract_job_requirements") as extract:
            with self.assertRaisesRegex(JobAnalysisError, "Add or fetch"):
                analyze_job_posting("  \n")

        extract.assert_not_called()

    def test_returns_validated_requirements(self):
        expected = JobRequirements(
            title="AI Solution Architect",
            responsibilities=["Design AI solutions"],
            required_skills=["Architecture"],
            preferred_skills=[],
            technologies=["Azure"],
            experience_requirements=["Five years of experience"],
        )
        with patch(
            "analysis.extract_job_requirements",
            return_value=expected,
        ) as extract:
            result = analyze_job_posting("  Job description  ")

        self.assertEqual(result, expected)
        extract.assert_called_once_with("Job description")

    def test_shows_configuration_errors_to_user(self):
        with patch(
            "analysis.extract_job_requirements",
            side_effect=AIConfigurationError("Set GEMINI_API_KEY."),
        ):
            with self.assertRaisesRegex(JobAnalysisError, "GEMINI_API_KEY"):
                analyze_job_posting("Job description")


class AnalyzeCvMatchTests(unittest.TestCase):
    def test_rejects_blank_job_or_cv_without_calling_model(self):
        with patch("analysis.request_cv_match") as request:
            with self.assertRaisesRegex(JobAnalysisError, "job description"):
                analyze_cv_match("  ", "CV text")
            with self.assertRaisesRegex(JobAnalysisError, "CV or profile"):
                analyze_cv_match("Job description", "  ")

        request.assert_not_called()

    def test_returns_match_report_with_trimmed_inputs(self):
        expected = CVMatchReport(
            fit_level="Strong match",
            summary="The CV supports the core qualifications.",
            strengths=["Python experience is directly described."],
            gaps=[],
            suggested_actions=["Tailor the CV to emphasize these examples."],
        )
        with patch(
            "analysis.request_cv_match",
            return_value=expected,
        ) as request:
            result = analyze_cv_match(" Job description ", " CV text ")

        self.assertEqual(result, expected)
        request.assert_called_once_with("Job description", "CV text")


if __name__ == "__main__":
    unittest.main()
