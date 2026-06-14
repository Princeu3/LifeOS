"""Withings data-API client (worker side): token refresh (signed) + getmeas (Bearer, unsigned).

Kept self-contained because the worker is deployed as its own service (separate build context from
the API). Shares only the tiny sign/getnonce idiom with app/withings.py. See docs/research/withings-api.md.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

import httpx

WBS = "https://wbsapi.withings.net"
MEASTYPES = "1,5,6,8,11,76,77,88"  # weight, lean, fat%, fat kg, hr, muscle, water, bone

CLIENT_ID = os.environ.get("WITHINGS_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("WITHINGS_CLIENT_SECRET", "")


def _sign(action: str, **signed: str) -> str:
    params = {"action": action, "client_id": CLIENT_ID, **signed}
    payload = ",".join(params[k] for k in sorted(params))
    return hmac.new(CLIENT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


async def _get_nonce(client: httpx.AsyncClient) -> str:
    ts = str(int(time.time()))
    r = await client.post(
        f"{WBS}/v2/signature",
        data={"action": "getnonce", "client_id": CLIENT_ID, "timestamp": ts,
              "signature": _sign("getnonce", timestamp=ts)},
    )
    r.raise_for_status()
    body = r.json()
    if body.get("status") != 0:
        raise RuntimeError(f"getnonce failed: {body}")
    return body["body"]["nonce"]


async def refresh(refresh_token: str) -> dict:
    """Exchange a refresh token for new tokens. Returns the requesttoken body (rotated tokens)."""
    async with httpx.AsyncClient(timeout=30) as client:
        nonce = await _get_nonce(client)
        r = await client.post(
            f"{WBS}/v2/oauth2",
            data={"action": "requesttoken", "client_id": CLIENT_ID, "grant_type": "refresh_token",
                  "refresh_token": refresh_token, "nonce": nonce, "signature": _sign("requesttoken", nonce=nonce)},
        )
        r.raise_for_status()
        body = r.json()
        if body.get("status") != 0:
            raise RuntimeError(f"token refresh failed: {body}")
        return body["body"]


async def getmeas(access_token: str, lastupdate: int) -> list[dict]:
    """Body-composition measure groups updated since `lastupdate` (epoch). Bearer auth, unsigned."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{WBS}/measure",
            data={"action": "getmeas", "meastypes": MEASTYPES, "category": 1, "lastupdate": lastupdate},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        body = r.json()
        if body.get("status") != 0:
            raise RuntimeError(f"getmeas failed: {body}")
        return body["body"].get("measuregrps", [])


# Withings meastype -> (our column, is_int)
TYPE_COL = {
    1: ("weight_kg", False),
    5: ("lean_mass_kg", False),
    6: ("fat_pct", False),
    8: ("fat_mass_kg", False),
    11: ("heart_rate", True),
    76: ("muscle_mass_kg", False),
    77: ("body_water_kg", False),
    88: ("bone_mass_kg", False),
}


def parse_group(grp: dict) -> dict:
    """measuregrp -> {column: value}. Real value = value * 10**unit."""
    out: dict = {}
    for m in grp.get("measures", []):
        col = TYPE_COL.get(m.get("type"))
        if not col:
            continue
        name, is_int = col
        value = m["value"] * (10 ** m["unit"])
        out[name] = int(round(value)) if is_int else round(value, 3)
    return out
