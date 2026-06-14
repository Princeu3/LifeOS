"""Withings router — OAuth connect + Notify webhook. Heavy getmeas+upsert is deferred to the worker.

Connect flow: /authorize (owner) -> Withings -> /callback (exchange code, subscribe webhook) ->
redirect back to the web app. On new data Withings POSTs /notify, which just defers a
`withings_sync` job and returns 200 fast (missed notifications aren't redelivered — the job
backfills via getmeas lastupdate). The webhook is validated by a query secret, not a signature
(Withings doesn't sign inbound POSTs).
"""

import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .. import withings
from ..auth import require_auth
from ..config import settings
from ..db import get_db
from ..procrastinate_app import defer

router = APIRouter(prefix="/withings", tags=["withings"])


def _callback_url() -> str:
    base = f"{settings.public_api_url}/withings/notify"
    return f"{base}?s={settings.withings_notify_secret}" if settings.withings_notify_secret else base


@router.get("/authorize")
async def authorize(_: uuid.UUID = Depends(require_auth)) -> dict:
    if not settings.withings_client_id:
        raise HTTPException(503, "Withings is not configured (set WITHINGS_CLIENT_ID/SECRET)")
    return {"url": withings.authorize_url(withings.make_state())}


@router.get("/callback")
async def callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    frontend = settings.frontend_origin or "https://os.princeuniverse.dev"
    if error or not code or not state or not withings.check_state(state):
        return RedirectResponse(f"{frontend}/?withings=error", status_code=303)
    await withings.exchange_code(db, code)
    try:
        await withings.subscribe(db, _callback_url())  # push notifications for body composition
    except Exception:  # noqa: BLE001 — connection still succeeds; the user can sync manually
        pass
    await defer("withings_sync", "withings")  # initial backfill
    return RedirectResponse(f"{frontend}/?withings=connected", status_code=303)


@router.head("/notify")
async def notify_verify() -> Response:
    # Withings sends a HEAD to verify the callback at subscribe time — must be 200.
    return Response(status_code=200)


@router.post("/notify")
async def notify(
    s: str | None = Query(default=None),
    appli: str | None = Form(default=None),
    startdate: int | None = Form(default=None),
    enddate: int | None = Form(default=None),
    userid: str | None = Form(default=None),
) -> Response:
    if settings.withings_notify_secret and s != settings.withings_notify_secret:
        raise HTTPException(403, "bad notify secret")
    # Return 200 FAST — defer the getmeas + upsert to the worker (it backfills via lastupdate).
    await defer("withings_sync", "withings", startdate=startdate, enddate=enddate)
    return Response(status_code=200)


@router.get("/status")
async def status(_: uuid.UUID = Depends(require_auth), db: AsyncSession = Depends(get_db)) -> dict:
    acct = await withings.get_account(db)
    return {
        "connected": acct is not None,
        "userid": acct.userid if acct else None,
        "last_sync_at": acct.last_sync_at if acct else None,
        "scope": acct.scope if acct else None,
    }


@router.post("/sync")
async def sync_now(_: uuid.UUID = Depends(require_auth), db: AsyncSession = Depends(get_db)) -> dict:
    if not await withings.get_account(db):
        raise HTTPException(400, "Withings not connected")
    await defer("withings_sync", "withings")
    return {"deferred": True}
