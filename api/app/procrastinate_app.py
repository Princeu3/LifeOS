"""Procrastinate App used by the API to DEFER jobs (the worker service runs them).

The tasks themselves are defined in worker/worker.py; here we defer by name via
`configure_task(name=..., queue=...)` so the API needn't import the task code. Opened/closed
in the FastAPI lifespan (see main.py). DSN is the plain libpq URL (PROCRASTINATE_DSN).
"""

from __future__ import annotations

from procrastinate import App, PsycopgConnector

from .config import settings

procrastinate_app = App(connector=PsycopgConnector(conninfo=settings.procrastinate_dsn))


async def defer(name: str, queue: str, **kwargs) -> None:
    await procrastinate_app.configure_task(name=name, queue=queue).defer_async(**kwargs)
