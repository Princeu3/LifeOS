"""Auth router — passkey (WebAuthn) registration, login, and recovery for the single owner.

These endpoints are intentionally NOT behind `require_auth` (they're how you obtain a session).
First-passkey registration is gated by `AUTH_BOOTSTRAP_TOKEN` (when set) to close the bootstrap
window; adding a 2nd passkey requires an active session.
"""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth
from ..config import settings
from ..db import get_db
from ..models import Credential
from ..schemas import LoginVerifyIn, RecoveryIn, RegisterOptionsIn, RegisterVerifyIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)) -> dict:
    count = await auth.count_credentials(db)
    cfg = await auth.get_auth_config(db)
    return {
        "registered": count > 0,
        "credentials": count,
        "max": auth.MAX_PASSKEYS,
        "recovery_set": bool(cfg and cfg.recovery_code_hash),
        "needs_bootstrap_token": count == 0 and bool(settings.auth_bootstrap_token),
    }


async def _authorize_registration(
    db: AsyncSession, authorization: str | None, bootstrap_token: str | None
) -> None:
    count = await auth.count_credentials(db)
    if count == 0:
        # First passkey: gate the open bootstrap window with a one-time token (if configured).
        if settings.auth_bootstrap_token and bootstrap_token != settings.auth_bootstrap_token:
            raise HTTPException(403, "bootstrap token required")
    elif count < auth.MAX_PASSKEYS:
        auth.require_auth(authorization)  # adding another passkey requires an active session
    else:
        raise HTTPException(409, "maximum passkeys already registered")


@router.post("/register/options")
async def register_options(
    body: RegisterOptionsIn,
    authorization: str | None = Header(default=None),
    x_bootstrap_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _authorize_registration(db, authorization, x_bootstrap_token)
    options, state = await auth.registration_options(db, body.name)
    await db.commit()  # persist auth_config if it was just created
    return {"options": options, "state": state}


@router.post("/register/verify")
async def register_verify(
    body: RegisterVerifyIn,
    authorization: str | None = Header(default=None),
    x_bootstrap_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _authorize_registration(db, authorization, x_bootstrap_token)
    challenge = auth.read_state(body.state, "reg")
    try:
        cred_id, public_key, sign_count = auth.verify_registration(body.response, challenge)
    except Exception as e:  # noqa: BLE001 — any verification failure is a 400
        raise HTTPException(400, "registration verification failed") from e

    first = (await auth.count_credentials(db)) == 0
    db.add(
        Credential(
            credential_id=cred_id,
            public_key=public_key,
            sign_count=sign_count,
            transports=(body.response.get("response") or {}).get("transports"),
            name=body.name or "passkey",
        )
    )
    recovery_code = None
    if first:
        cfg = await auth.ensure_auth_config(db)
        recovery_code, cfg.recovery_code_hash = auth.gen_recovery_code()
    await db.commit()
    # Issue a session so the user is logged in immediately after registering.
    return {"verified": True, "token": auth.make_session(), "recovery_code": recovery_code}


@router.post("/login/options")
async def login_options(db: AsyncSession = Depends(get_db)) -> dict:
    if (await auth.count_credentials(db)) == 0:
        raise HTTPException(400, "no passkeys registered yet")
    options, state = await auth.authentication_options(db)
    return {"options": options, "state": state}


@router.post("/login/verify")
async def login_verify(body: LoginVerifyIn, db: AsyncSession = Depends(get_db)) -> dict:
    challenge = auth.read_state(body.state, "auth")
    cred = (
        await db.execute(
            select(Credential).where(Credential.credential_id == body.response.get("id"))
        )
    ).scalar_one_or_none()
    if not cred:
        raise HTTPException(400, "unknown credential")
    try:
        cred.sign_count = auth.verify_authentication(body.response, challenge, cred)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(401, "authentication failed") from e
    cred.last_used_at = func.now()
    await db.commit()
    return {"token": auth.make_session()}


@router.post("/recovery")
async def recovery(body: RecoveryIn, db: AsyncSession = Depends(get_db)) -> dict:
    cfg = await auth.get_auth_config(db)
    if not cfg or not auth.check_recovery_code(body.code, cfg.recovery_code_hash):
        raise HTTPException(401, "invalid recovery code")
    # Single-use: rotate to a fresh code (shown once) and hand back a session.
    new_code, cfg.recovery_code_hash = auth.gen_recovery_code()
    await db.commit()
    return {"token": auth.make_session(), "recovery_code": new_code}


@router.get("/credentials")
async def list_credentials(
    _: uuid.UUID = Depends(auth.require_auth), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    creds = (await db.execute(select(Credential).order_by(Credential.created_at))).scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "created_at": c.created_at,
            "last_used_at": c.last_used_at,
        }
        for c in creds
    ]


@router.delete("/credentials/{cred_id}")
async def delete_credential(
    cred_id: uuid.UUID,
    _: uuid.UUID = Depends(auth.require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cred = await db.get(Credential, cred_id)
    if cred:
        await db.delete(cred)
        await db.commit()
    return {"deleted": True}
