"""Object storage (Cloudflare R2, S3-compatible) + app-side AES-256-GCM for sensitive media.

Non-sensitive media is stored as-is. Sensitive (body/medical) media is encrypted with
MEDIA_ENCRYPTION_KEY before upload, so R2 holds only ciphertext. Serve via presigned URLs
(client <-> bucket direct) to avoid proxying bytes through the API.
"""

from __future__ import annotations

import base64
import os

import boto3
from botocore.config import Config
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import settings

_s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key,
    region_name=settings.s3_region,
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},  # R2 prefers path-style on the S3 endpoint
        # boto3/botocore >=1.36 add CRC32 checksums R2 rejects → require-only (Jan-2025 gotcha)
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    ),
)


def presigned_get(key: str, ttl: int = 3600) -> str:
    return _s3.generate_presigned_url(
        "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=ttl
    )


def presigned_put(key: str, ttl: int = 3600) -> str:
    return _s3.generate_presigned_url(
        "put_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=ttl
    )


def new_nonce() -> bytes:
    return os.urandom(12)


def _aesgcm() -> AESGCM:
    if not settings.media_encryption_key:
        raise RuntimeError("MEDIA_ENCRYPTION_KEY not set")
    return AESGCM(base64.b64decode(settings.media_encryption_key))


def encrypt_bytes(plaintext: bytes, nonce: bytes) -> bytes:
    """AES-256-GCM. Store the 12-byte nonce alongside the object key."""
    return _aesgcm().encrypt(nonce, plaintext, None)


def decrypt_bytes(ciphertext: bytes, nonce: bytes) -> bytes:
    return _aesgcm().decrypt(nonce, ciphertext, None)
