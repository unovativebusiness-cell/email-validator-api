"""Authenticated HTTP API for verifying one or more email addresses."""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from email_validator import EmailNotValidError, validate_email
from email_validator.deliverability import caching_resolver

API_SECRET = os.environ.get("EMAIL_API_SECRET", "").strip()
CHECK_DELIVERABILITY = os.environ.get("CHECK_DELIVERABILITY", "true").strip().lower() not in (
    "",
    "0",
    "false",
    "no",
    "off",
)
MAX_EMAILS = int(os.environ.get("MAX_EMAILS", "50"))

app = FastAPI(
    title="Email Validator API",
    description="Verify one or more email addresses (comma-separated). Authenticate with EMAIL_API_SECRET.",
    version="1.0.0",
)


class VerifyRequest(BaseModel):
    emails: str | list[str] = Field(
        ...,
        description="Comma-separated emails, or a JSON array of emails.",
        examples=["alice@example.com, bob@example.org"],
    )
    check_deliverability: bool | None = Field(
        default=None,
        description="Override server default for MX/deliverability checks.",
    )


class EmailResult(BaseModel):
    email: str
    valid: bool
    normalized: str | None = None
    error: str | None = None


class VerifyResponse(BaseModel):
    count: int
    valid_count: int
    invalid_count: int
    results: list[EmailResult]


@lru_cache(maxsize=1)
def _resolver() -> Any:
    return caching_resolver()


def _parse_emails(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        parts = raw
    else:
        parts = raw.split(",")
    emails: list[str] = []
    seen: set[str] = set()
    for part in parts:
        email = str(part).strip()
        if not email:
            continue
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        emails.append(email)
    return emails


def _verify_one(email: str, *, check_deliverability: bool) -> EmailResult:
    try:
        info = validate_email(
            email,
            check_deliverability=check_deliverability,
            dns_resolver=_resolver() if check_deliverability else None,
        )
        return EmailResult(email=email, valid=True, normalized=info.normalized)
    except EmailNotValidError as exc:
        return EmailResult(email=email, valid=False, error=str(exc))


def require_secret(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: EMAIL_API_SECRET is not set.",
        )

    provided: str | None = None
    if x_api_key:
        provided = x_api_key.strip()
    elif authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            provided = token.strip()
        else:
            provided = authorization.strip()

    if not provided or not secrets.compare_digest(provided, API_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API secret.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _run_verify(
    raw_emails: str | list[str],
    check_deliverability: bool | None,
) -> VerifyResponse:
    emails = _parse_emails(raw_emails)
    if not emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one email address.",
        )
    if len(emails) > MAX_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many emails (max {MAX_EMAILS}).",
        )

    deliverability = CHECK_DELIVERABILITY if check_deliverability is None else check_deliverability
    results = [_verify_one(email, check_deliverability=deliverability) for email in emails]
    valid_count = sum(1 for r in results if r.valid)
    return VerifyResponse(
        count=len(results),
        valid_count=valid_count,
        invalid_count=len(results) - valid_count,
        results=results,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/verify", response_model=VerifyResponse, dependencies=[Depends(require_secret)])
def verify_get(
    emails: str = Query(..., description="Comma-separated email addresses"),
    check_deliverability: bool | None = Query(default=None),
) -> VerifyResponse:
    return _run_verify(emails, check_deliverability)


@app.post("/v1/verify", response_model=VerifyResponse, dependencies=[Depends(require_secret)])
def verify_post(body: VerifyRequest) -> VerifyResponse:
    return _run_verify(body.emails, body.check_deliverability)
