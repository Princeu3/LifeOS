from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres — async app driver = psycopg 3; Alembic uses the same URL synchronously.
    database_url: str = "postgresql+psycopg://lifeos:lifeos@localhost:5432/lifeos"
    procrastinate_dsn: str = "postgresql://lifeos:lifeos@localhost:5432/lifeos"  # libpq for the queue
    frontend_origin: str | None = None  # deployed web origin, added to CORS allow-list

    # AI — chat/vision/image-gen ALL via OpenRouter (one key); embeddings + STT direct.
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_zdr: bool = True  # send provider.zdr=true + data_collection=deny on every call
    voyage_api_key: str | None = None      # Voyage 4 embeddings — not on OpenRouter
    elevenlabs_api_key: str | None = None  # Scribe v2 STT — not on OpenRouter
    media_encryption_key: str | None = None  # AES-256 (base64) for sensitive media at rest

    # --- model routing (OpenRouter slugs verified 2026-06-13; keep in sync with CLAUDE.md) ---
    capture_model: str = "openrouter/anthropic/claude-haiku-4.5"
    insight_model: str = "openrouter/anthropic/claude-sonnet-4.6"
    vision_health_model: str = "openrouter/anthropic/claude-sonnet-4.6"
    vision_object_model: str = "openrouter/google/gemini-3.5-flash"
    classify_model: str = "openrouter/google/gemini-3.1-flash-lite"
    image_edit_model: str = "openrouter/google/gemini-3.1-flash-image-preview"  # wardrobe only
    embedding_model: str = "voyage-4"  # LAZY: generated only when the chat phase ships

    # Object storage — Cloudflare R2 (S3-compatible). Stores only AES ciphertext for sensitive media.
    s3_endpoint: str | None = None       # https://<account>.r2.cloudflarestorage.com
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str = "lifeos-media"
    s3_region: str = "auto"

    # --- auth (passkeys / WebAuthn) — see app/auth.py, docs/research grounding ---
    auth_secret: str = "dev-insecure-change-me"  # signs session/state/media tokens (SET in prod)
    auth_bootstrap_token: str | None = None       # gates the FIRST passkey registration (set in prod)
    webauthn_rp_id: str | None = None             # default: hostname of frontend_origin (e.g. web-...up.railway.app)
    webauthn_rp_name: str = "LifeOS"
    webauthn_origin: str | None = None            # default: frontend_origin (the https URL the ceremony runs on)
    session_ttl_days: int = 7
    media_token_ttl_seconds: int = 900            # short-lived per-photo <img> token

    # Withings (body composition auto-sync — see docs/research/withings-api.md)
    withings_client_id: str | None = None
    withings_client_secret: str | None = None
    withings_redirect_uri: str | None = None  # must EXACTLY match the dev-app registration
    withings_notify_secret: str | None = None  # query secret to validate incoming webhook POSTs
    public_api_url: str = "https://api.os.princeuniverse.dev"  # public API base (redirect/callback URLs)

    @property
    def sqlalchemy_url(self) -> str:
        """Async SQLAlchemy URL. Railway provides plain `postgresql://`; psycopg driver is required."""
        u = self.database_url
        if u.startswith("postgresql://"):
            return "postgresql+psycopg://" + u[len("postgresql://") :]
        return u


settings = Settings()
