"""Passkey (WebAuthn) auth + signed tokens for the single-user owner.

One owner, up to 2 passkeys + a single-use recovery code. Sessions are STATELESS signed bearer
tokens (no cross-site cookies — the frontend and API are on different domains). `rp_id`/`origin`
are pinned from config (derived from FRONTEND_ORIGIN), never from request headers. Per the grounding:
*.up.railway.app is a public suffix, so the frontend host is a valid rp_id today, but a custom
domain is recommended for durability (Railway hostname churn would invalidate passkeys).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from urllib.parse import urlparse

from fastapi import Header, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, generate_user_handle
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .config import settings
from .models import AuthConfig, Credential

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
MAX_PASSKEYS = 2

_serializer = URLSafeTimedSerializer(settings.auth_secret)


# --- relying-party config (env-pinned, never request-derived) ---
def rp_id() -> str:
    if settings.webauthn_rp_id:
        return settings.webauthn_rp_id
    origin = settings.webauthn_origin or settings.frontend_origin
    return (urlparse(origin).hostname or "localhost") if origin else "localhost"


def expected_origin() -> str:
    return settings.webauthn_origin or settings.frontend_origin or "http://localhost:5173"


# --- tokens: session (bearer), webauthn challenge state, media (<img>) ---
def make_session() -> str:
    return _serializer.dumps({"sub": str(OWNER_ID)}, salt="session")


def _verify_session(token: str) -> bool:
    try:
        data = _serializer.loads(token, salt="session", max_age=settings.session_ttl_days * 86400)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("sub") == str(OWNER_ID)


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def require_auth(authorization: str | None = Header(default=None)) -> uuid.UUID:
    """FastAPI dependency: 401 unless a valid session bearer token is present."""
    token = _bearer(authorization)
    if not token or not _verify_session(token):
        raise HTTPException(status_code=401, detail="authentication required")
    return OWNER_ID


def make_state(challenge: bytes, kind: str) -> str:
    return _serializer.dumps({"c": bytes_to_base64url(challenge), "k": kind}, salt="webauthn-state")


def read_state(state: str, kind: str) -> bytes:
    try:
        data = _serializer.loads(state, salt="webauthn-state", max_age=300)
    except (BadSignature, SignatureExpired) as e:
        raise HTTPException(400, "challenge expired — please retry") from e
    if data.get("k") != kind:
        raise HTTPException(400, "challenge type mismatch")
    return base64url_to_bytes(data["c"])


def make_media_token(photo_id: uuid.UUID) -> str:
    return _serializer.dumps({"pid": str(photo_id)}, salt="media")


def _verify_media_token(token: str | None, photo_id: uuid.UUID) -> bool:
    if not token:
        return False
    try:
        data = _serializer.loads(token, salt="media", max_age=settings.media_token_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("pid") == str(photo_id)


def image_auth_ok(token: str | None, authorization: str | None, photo_id: uuid.UUID) -> bool:
    """An <img> can carry a short-lived per-photo media token (?t=) instead of a bearer header."""
    if _verify_media_token(token, photo_id):
        return True
    bearer = _bearer(authorization)
    return bool(bearer and _verify_session(bearer))


# --- recovery code (single-use, hashed at rest) ---
def gen_recovery_code() -> tuple[str, str]:
    code = secrets.token_urlsafe(18)  # ~144 bits of entropy -> a fast hash is fine
    return code, hashlib.sha256(code.encode()).hexdigest()


def check_recovery_code(code: str, code_hash: str | None) -> bool:
    if not code_hash:
        return False
    return secrets.compare_digest(hashlib.sha256(code.encode()).hexdigest(), code_hash)


# --- DB helpers ---
async def count_credentials(db: AsyncSession) -> int:
    return (await db.execute(select(func.count()).select_from(Credential))).scalar_one()


async def get_auth_config(db: AsyncSession) -> AuthConfig | None:
    return (await db.execute(select(AuthConfig).limit(1))).scalar_one_or_none()


async def ensure_auth_config(db: AsyncSession) -> AuthConfig:
    cfg = await get_auth_config(db)
    if cfg is None:
        cfg = AuthConfig(webauthn_user_id=bytes_to_base64url(generate_user_handle()))
        db.add(cfg)
        await db.flush()
    return cfg


# --- WebAuthn ceremonies ---
async def registration_options(db: AsyncSession, name: str | None) -> tuple[dict, str]:
    cfg = await ensure_auth_config(db)
    existing = (await db.execute(select(Credential))).scalars().all()
    opts = generate_registration_options(
        rp_id=rp_id(),
        rp_name=settings.webauthn_rp_name,
        user_name="owner",
        user_display_name="LifeOS Owner",
        user_id=base64url_to_bytes(cfg.webauthn_user_id),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existing
        ],
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    return json.loads(options_to_json(opts)), make_state(opts.challenge, "reg")


def verify_registration(response: dict, challenge: bytes) -> tuple[str, str, int]:
    v = verify_registration_response(
        credential=json.dumps(response),
        expected_challenge=challenge,
        expected_rp_id=rp_id(),
        expected_origin=expected_origin(),
        require_user_verification=False,
    )
    return (
        bytes_to_base64url(v.credential_id),
        bytes_to_base64url(v.credential_public_key),
        v.sign_count,
    )


async def authentication_options(db: AsyncSession) -> tuple[dict, str]:
    existing = (await db.execute(select(Credential))).scalars().all()
    opts = generate_authentication_options(
        rp_id=rp_id(),
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existing
        ],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return json.loads(options_to_json(opts)), make_state(opts.challenge, "auth")


def verify_authentication(response: dict, challenge: bytes, cred: Credential) -> int:
    v = verify_authentication_response(
        credential=json.dumps(response),
        expected_challenge=challenge,
        expected_rp_id=rp_id(),
        expected_origin=expected_origin(),
        credential_public_key=base64url_to_bytes(cred.public_key),
        credential_current_sign_count=cred.sign_count,
        require_user_verification=False,
    )
    return v.new_sign_count
