"""Photo-capture vertical slice.

Upload a face/skin/body/nails/hair photo -> store in R2 (AES-256-GCM encrypted at rest when
`sensitive`) -> run ZDR Claude vision (unless `exclude_from_cloud_ai`) -> persist a Photo row +
a `photo` TimelineEvent. Images are served back through `/photos/{id}/image`, which decrypts
sensitive media on read (so the bucket only ever holds ciphertext for those).

Privacy rules enforced here:
- Sensitive (body/medical/identity) bytes are AES-encrypted BEFORE they touch R2.
- Vision runs only when `exclude_from_cloud_ai` is False, and only via the ZDR Claude model
  (see app/vision.py) — never nano-banana.
- Sync boto3 / crypto calls are pushed to a threadpool so they don't block the event loop.
"""

import base64
import binascii
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..auth import image_auth_ok, make_media_token, require_auth
from ..db import get_db
from ..models import Domain, Photo, Source, TimelineEvent
from ..schemas import PhotoOut, PhotoRef
from ..vision import analyze_photo

router = APIRouter(prefix="/photos", tags=["photos"])

OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

PHOTO_TYPES = {"face", "skin", "body", "nails", "hair"}
SENSITIVE_BY_DEFAULT = {"face", "skin", "body", "nails"}  # hair defaults non-sensitive
MAX_BYTES = 25 * 1024 * 1024  # 25 MB cap (Starlette has no built-in body limit)

# Magic-byte signatures -> mime. Trust the bytes, not the client-sent content-type.
_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def _sniff_image(data: bytes) -> str | None:
    for sig, mime in _SIGNATURES:
        if data.startswith(sig):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"mif1", b"msf1"):
        return "image/heic"
    return None


async def _read_capped(file: UploadFile) -> bytes:
    chunks, total = [], 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_BYTES:
            raise HTTPException(413, f"image exceeds {MAX_BYTES // (1024 * 1024)} MB cap")
        chunks.append(chunk)
    return b"".join(chunks)


async def _latest_of_type(db: AsyncSession, photo_type: str) -> Photo | None:
    return (
        await db.execute(
            select(Photo).where(Photo.photo_type == photo_type).order_by(Photo.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()


def _safe_name(name: str | None, mime: str) -> str:
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
           "image/gif": "gif", "image/heic": "heic"}.get(mime, "bin")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", (name or "photo").rsplit("/", 1)[-1])[:64]
    return base if base.lower().endswith(f".{ext}") else f"{base}.{ext}"


@router.post("", response_model=PhotoOut)
async def upload_photo(
    file: UploadFile = File(...),
    photo_type: str = Form(...),
    notes: str | None = Form(None),
    sensitive: bool | None = Form(None),
    exclude_from_cloud_ai: bool = Form(False),
    occurred_at: str | None = Form(None),
    prev_photo_id: str | None = Form(None),
    _: uuid.UUID = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> PhotoOut:
    if photo_type not in PHOTO_TYPES:
        raise HTTPException(422, f"photo_type must be one of {sorted(PHOTO_TYPES)}")

    raw = await _read_capped(file)
    mime = _sniff_image(raw)
    if not mime:
        raise HTTPException(415, "file is not a recognized image (jpeg/png/webp/gif/heic)")

    is_sensitive = sensitive if sensitive is not None else (photo_type in SENSITIVE_BY_DEFAULT)
    photo_id = uuid.uuid4()
    fname = _safe_name(file.filename, mime)
    key = f"media/photo/{photo_id}/{fname}" + (".enc" if is_sensitive else "")

    # Encrypt sensitive bytes app-side so R2 only ever holds ciphertext.
    enc_nonce: str | None = None
    if is_sensitive:
        nonce = storage.new_nonce()
        ciphertext = await run_in_threadpool(storage.encrypt_bytes, raw, nonce)
        enc_nonce = base64.b64encode(nonce).decode()
        await run_in_threadpool(storage.put_bytes, key, ciphertext, "application/octet-stream")
    else:
        await run_in_threadpool(storage.put_bytes, key, raw, mime)

    # Vision on the PLAINTEXT bytes, only if the user hasn't opted this image out of cloud AI.
    vision = None
    if not exclude_from_cloud_ai:
        vision = await analyze_photo(raw, mime, photo_type)

    occurred = datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(timezone.utc)
    # Auto-chain to the previous same-type photo (ghost-overlay reference) unless one was given.
    prev_id = uuid.UUID(prev_photo_id) if prev_photo_id else None
    if prev_id is None:
        prev = await _latest_of_type(db, photo_type)
        prev_id = prev.id if prev else None

    photo = Photo(
        id=photo_id,
        photo_type=photo_type,
        bucket_key=key,
        prev_photo_id=prev_id,
        analysis=(vision or {}).get("analysis") if vision else None,
        ai_model=(vision or {}).get("model") if vision else None,
        ai_confidence=(vision or {}).get("confidence") if vision else None,
        sensitive=is_sensitive,
        exclude_from_cloud_ai=exclude_from_cloud_ai,
        enc_nonce=enc_nonce,
        content_type=mime,
        notes=notes,
    )
    db.add(photo)

    obs = (vision or {}).get("analysis", {}).get("observations") if vision else None
    summary = f"{photo_type.title()} photo" + (f" — {obs[0]}" if obs else "")
    event = TimelineEvent(
        user_id=OWNER_ID,
        occurred_at=occurred,
        domain=Domain.photo,
        source=Source.photo,
        ref_table="photos",
        ref_id=photo_id,
        summary=summary,
        structured={
            "photo_type": photo_type,
            "sensitive": is_sensitive,
            **({"analysis": vision["analysis"], "prompt_version": vision["prompt_version"]} if vision else {}),
            **({"notes": notes} if notes else {}),
        },
        media=[{"bucket_key": key, "photo_id": str(photo_id)}],
        confidence=(vision or {}).get("confidence") if vision else None,
    )
    db.add(event)
    await db.commit()

    out = PhotoOut.model_validate(photo)
    out.event_id = event.id
    return out


@router.get("/latest", response_model=PhotoRef | None)
async def latest_photo(
    photo_type: str = Query(...),
    _: uuid.UUID = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> PhotoRef | None:
    """Most recent photo of a type — the ghost-overlay reference for the next capture."""
    if photo_type not in PHOTO_TYPES:
        raise HTTPException(422, f"photo_type must be one of {sorted(PHOTO_TYPES)}")
    photo = await _latest_of_type(db, photo_type)
    if not photo:
        return None
    return PhotoRef(
        id=photo.id,
        photo_type=photo.photo_type,
        created_at=photo.created_at,
        media_token=make_media_token(photo.id),  # so the composer can load the ghost <img>
    )


@router.get("/{photo_id}", response_model=PhotoOut)
async def get_photo(
    photo_id: uuid.UUID,
    _: uuid.UUID = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Photo:
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(404, "photo not found")
    return photo


@router.get("/{photo_id}/image")
async def get_photo_image(
    photo_id: uuid.UUID,
    t: str | None = Query(default=None),  # short-lived per-photo media token (for <img src>)
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # <img> can't send Authorization; accept a scoped media token via ?t= OR a bearer header.
    if not image_auth_ok(t, authorization, photo_id):
        raise HTTPException(401, "authentication required")
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(404, "photo not found")
    data = await run_in_threadpool(storage.get_bytes, photo.bucket_key)
    if photo.sensitive:
        if not photo.enc_nonce:
            raise HTTPException(500, "sensitive photo missing encryption nonce")
        try:
            nonce = base64.b64decode(photo.enc_nonce)
            data = await run_in_threadpool(storage.decrypt_bytes, data, nonce)
        except (binascii.Error, ValueError) as e:
            raise HTTPException(500, "failed to decrypt photo") from e
    return Response(
        content=data,
        media_type=photo.content_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=3600"},
    )
