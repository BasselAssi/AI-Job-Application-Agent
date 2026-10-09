from typing import Any, List, Literal

from pydantic import BaseModel, ConfigDict, Field


def _remove_unsupported_additional_properties(schema: dict[str, Any]) -> None:
    schema.pop("additionalProperties", None)
    for value in schema.values():
        if isinstance(value, dict):
            _remove_unsupported_additional_properties(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _remove_unsupported_additional_properties(item)


class JobRequirements(BaseModel):
    """Structured job requirements extracted from a posting."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=_remove_unsupported_additional_properties,
    )

    title: str = Field(description="The job title, or an empty string if not stated.")
    responsibilities: List[str] = Field(
        description="Responsibilities explicitly described in the posting."
    )
    required_skills: List[str] = Field(
        description="Skills explicitly required by the posting."
    )
    preferred_skills: List[str] = Field(
        description="Skills explicitly preferred or considered an asset."
    )
    technologies: List[str] = Field(
        description="Tools, platforms, programming languages, and technologies named."
    )
    experience_requirements: List[str] = Field(
        description="Required years, seniority, and relevant experience stated."
    )


class CVMatchReport(BaseModel):
    """Evidence-based comparison of a CV/profile with a job posting."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=_remove_unsupported_additional_properties,
    )

    fit_level: Literal["Strong match", "Potential match", "Weak match"] = Field(
        description="A qualitative overall fit; do not provide a numerical score."
    )
    summary: str = Field(
        description="A concise explanation of the overall fit and its main caveat."
    )
    strengths: List[str] = Field(
        description=(
            "Job requirements supported by specific evidence in the CV/profile."
        )
    )
    gaps: List[str] = Field(
        description=(
            "Important requirements without clear CV/profile evidence, phrased as "
            "unconfirmed rather than assumed deficiencies."
        )
    )
    suggested_actions: List[str] = Field(
        description=(
            "Practical suggestions for clarifying evidence or addressing gaps."
        )
    )
