import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from ai_client import (
    AIConfigurationError,
    assess_cv_match,
    extract_job_requirements,
)
from models import CVMatchReport, JobRequirements


class GeminiClientTests(unittest.TestCase):
    def test_response_schema_omits_unsupported_additional_properties(self):
        schema = JobRequirements.model_json_schema()

        self.assertNotIn("additionalProperties", schema)

    def test_response_validation_still_rejects_unexpected_fields(self):
        with self.assertRaises(ValidationError):
            JobRequirements.model_validate(
                {
                    "title": "",
                    "responsibilities": [],
                    "required_skills": [],
                    "preferred_skills": [],
                    "technologies": [],
                    "experience_requirements": [],
                    "unexpected": "value",
                }
            )

    def test_match_schema_omits_unsupported_additional_properties(self):
        schema = CVMatchReport.model_json_schema()

        self.assertNotIn("additionalProperties", schema)

    def test_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                AIConfigurationError,
                "GEMINI_API_KEY",
            ):
                extract_job_requirements("Job description")

    def test_sends_only_job_text_and_returns_structured_response(self):
        requirements = JobRequirements(
            title="AI Solution Architect",
            responsibilities=["Design AI solutions"],
            required_skills=["Architecture"],
            preferred_skills=[],
            technologies=["Azure"],
            experience_requirements=["Five years of experience"],
        )
        response = SimpleNamespace(text=requirements.model_dump_json())
        generate_content = unittest.mock.Mock(return_value=response)
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            with patch("ai_client.genai.Client", return_value=client) as client_factory:
                result = extract_job_requirements("The job posting text")

        self.assertEqual(result, requirements)
        client_factory.assert_called_once()
        self.assertEqual(client_factory.call_args.kwargs["api_key"], "test-key")
        retry_options = client_factory.call_args.kwargs[
            "http_options"
        ].retry_options
        self.assertEqual(retry_options.attempts, 3)
        self.assertEqual(retry_options.http_status_codes, [503])
        call = generate_content.call_args.kwargs
        self.assertEqual(call["model"], "gemini-flash-latest")
        self.assertIn("The job posting text", call["contents"])
        self.assertNotIn("CV", call["contents"])
        self.assertEqual(call["config"].response_schema, JobRequirements)
        self.assertEqual(call["config"].response_mime_type, "application/json")

    def test_match_request_sends_job_and_cv_and_returns_report(self):
        report = CVMatchReport(
            fit_level="Potential match",
            summary="Several core requirements have evidence, with one gap.",
            strengths=["Python experience is supported by the CV."],
            gaps=["No cloud platform experience is stated in the CV."],
            suggested_actions=["Add relevant cloud project details if applicable."],
        )
        response = SimpleNamespace(text=report.model_dump_json())
        generate_content = unittest.mock.Mock(return_value=response)
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            with patch("ai_client.genai.Client", return_value=client):
                result = assess_cv_match(
                    "Job requires Python and cloud experience.",
                    "CV: Built Python services.",
                )

        self.assertEqual(result, report)
        call = generate_content.call_args.kwargs
        self.assertIn("Job requires Python and cloud experience.", call["contents"])
        self.assertIn("CV: Built Python services.", call["contents"])
        self.assertEqual(call["config"].response_schema, CVMatchReport)


if __name__ == "__main__":
    unittest.main()
