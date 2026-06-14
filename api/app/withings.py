"""Withings OAuth + Notify (API side). See docs/research/withings-api.md.

THE GOTCHA: `getnonce` and `requesttoken` (and Notify) are signed — signature = HMAC-SHA256 of the
comma-joined param VALUES sorted by key, keyed by client_secret, plus a `nonce` from getnonce. Data
API calls (getmeas) are NOT signed (just Bearer) and live in the worker. Tokens rotate: persist the
new refresh_token atomically on every refresh (the worker does refreshes; the API only exchanges the
auth code and subscribes right after, while the token is fresh).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import WithingsAccount

WBS = "https://wbsapi.withings.net"
AUTHORIZE = "https://account.withings.com/oauth2_user/authorize2"
SCOPE = "user.metrics"
MEASTYPES = "1,5,6,8,11,76,77,88"  # weight, lean, fat%, fat kg, hr, muscle, water, bone

_state = URLSafeTimedSerializer(settings.auth_secret, salt="withings-state")


def redirect_uri() -> str:
    return settings.withings_redirect_uri or f"{settings.public_api_url}/withings/callback"


def make_state() -> str:
    return _state.dumps({"k": "withings"})


def check_state(state: str) -> bool:
    try:
        _state.loads(state, max_age=600)
        return True
    except (BadSignature, SignatureExpired):
        return False


def authorize_url(state: str, demo: bool = False) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.withings_client_id,
        "scope": SCOPE,
        "redirect_uri": redirect_uri(),
        "state": state,
    }
    if demo:
        params["mode"] = "demo"
    return f"{AUTHORIZE}?{urlencode(params)}"


def _sign(action: str, **signed_params: str) -> str:
    """signature = HMAC-SHA256(client_secret, ",".join(values sorted by key))."""
    params = {"action": action, "client_id": settings.withings_client_id, **signed_params}
    payload = ",".join(params[k] for k in sorted(params))
    return hmac.new(
        settings.withings_client_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


async def _get_nonce(client: httpx.AsyncClient) -> str:
    ts = str(int(time.time()))
    data = {
        "action": "getnonce",
        "client_id": settings.withings_client_id,
        "timestamp": ts,
        "signature": _sign("getnonce", timestamp=ts),
    }
    r = await client.post(f"{WBS}/v2/signature", data=data)
    r.raise_for_status()
    body = r.json()
    if body.get("status") != 0:
        raise RuntimeError(f"withings getnonce failed: {body}")
    return body["body"]["nonce"]


async def _persist(db: AsyncSession, body: dict) -> WithingsAccount:
    """Upsert the single account from a requesttoken response body."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(body.get("expires_in", 10800)))
    userid = str(body["userid"])
    acct = (await db.execute(select(WithingsAccount).where(WithingsAccount.userid == userid))).scalar_one_or_none()
    if acct is None:
        acct = WithingsAccount(userid=userid)
        db.add(acct)
    acct.access_token = body["access_token"]
    acct.refresh_token = body["refresh_token"]
    acct.expires_at = expires_at
    acct.scope = body.get("scope")
    acct.updated_at = datetime.now(timezone.utc)
    return acct


async def exchange_code(db: AsyncSession, code: str) -> WithingsAccount:
    async with httpx.AsyncClient(timeout=30) as client:
        nonce = await _get_nonce(client)
        data = {
            "action": "requesttoken",
            "client_id": settings.withings_client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(),
            "nonce": nonce,
            "signature": _sign("requesttoken", nonce=nonce),
        }
        r = await client.post(f"{WBS}/v2/oauth2", data=data)
        r.raise_for_status()
        body = r.json()
        if body.get("status") != 0:
            raise RuntimeError(f"withings token exchange failed: {body}")
        acct = await _persist(db, body["body"])
    await db.commit()
    await db.refresh(acct)
    return acct


async def subscribe(db: AsyncSession, callbackurl: str) -> dict:
    """Subscribe the Notify webhook for appli=1 (weight & body composition)."""
    acct = await get_account(db)
    if not acct:
        raise RuntimeError("no withings account connected")
    async with httpx.AsyncClient(timeout=30) as client:
        nonce = await _get_nonce(client)
        data = {
            "action": "subscribe",
            "client_id": settings.withings_client_id,
            "callbackurl": callbackurl,
            "appli": "1",
            "nonce": nonce,
            "signature": _sign("subscribe", nonce=nonce),
        }
        r = await client.post(
            f"{WBS}/notify",
            data=data,
            headers={"Authorization": f"Bearer {acct.access_token}"},
        )
        r.raise_for_status()
        return r.json()


async def get_account(db: AsyncSession) -> WithingsAccount | None:
    return (await db.execute(select(WithingsAccount).limit(1))).scalar_one_or_none()
