"""Backward compat - import from app.app instead.

Kept so `from app.api.main import app` still works for tests.
New code should use `from app.app import app` or `create_app()`.
"""

from app.app import app, create_app

__all__ = ["app", "create_app"]
