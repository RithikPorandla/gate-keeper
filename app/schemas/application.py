from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

# Loose EIN-like check for the demo: 9 digits, optionally with a dash (NN-NNNNNNN).
_EIN_RE = re.compile(r"^\d{2}-?\d{7}$")


class ApplicationCreate(BaseModel):
    """Inbound application payload. Free-text fields are treated as untrusted data."""

    business_name: str = Field(min_length=1, max_length=255)
    registration_number: str = Field(min_length=1, max_length=64)
    country: str = Field(min_length=2, max_length=2, description="ISO-3166 alpha-2")
    industry_code: str = Field(min_length=1, max_length=16)
    requested_spend_limit: float = Field(gt=0, le=10_000_000)

    applicant_name: str = Field(min_length=1, max_length=255)
    applicant_email: EmailStr
    applicant_dob: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    mock_credit_score: int | None = Field(default=None, ge=300, le=850)

    @field_validator("country")
    @classmethod
    def upper_country(cls, v: str) -> str:
        return v.upper()

    @field_validator("registration_number")
    @classmethod
    def strip_registration(cls, v: str) -> str:
        return v.strip()

    def is_ein_well_formed(self) -> bool:
        return bool(_EIN_RE.match(self.registration_number))


class ApplicationOut(BaseModel):
    id: str
    status: str
