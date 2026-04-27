"""Pydantic models for email OTP authentication."""

from pydantic import BaseModel, EmailStr, Field


class SendEmailOtpRequestBody(BaseModel):
    """Request body for initiating an email OTP challenge."""

    email: EmailStr = Field(
        description="Recipient email address that will receive the six-digit OTP code.",
    )


class SendEmailOtpResponseBody(BaseModel):
    """Response after an OTP email is accepted for delivery."""

    message: str = Field(
        description="Human-readable status message confirming the OTP send request.",
    )


class VerifyEmailOtpRequestBody(BaseModel):
    """Request body for verifying an email OTP and receiving a JWT."""

    email: EmailStr = Field(
        description="Email address that received the OTP code.",
    )
    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Six-digit numeric OTP code delivered by email.",
    )


class VerifyEmailOtpResponseBody(BaseModel):
    """Response containing a JWT after successful OTP verification."""

    access_token: str = Field(
        description="Bearer token to authorize subsequent FishSniper API calls.",
    )
    is_new_user: bool = Field(
        description="True when this verification created a new `users` row for the email.",
    )


class OtpErrorResponseBody(BaseModel):
    """Standard error payload for OTP failures."""

    error: str = Field(description="Short error message suitable for display or logging.")
