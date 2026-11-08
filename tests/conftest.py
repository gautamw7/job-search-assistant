"""Test isolation.

The environment must be set BEFORE any ``app`` module is imported, because paths
(DATA_DIR, LOGS_DIR) are resolved at import time. Without this, tests wrote fake
PDFs, communication styles and API keys into the developer's real data folder.
"""

import os
import tempfile

_SANDBOX = tempfile.mkdtemp(prefix="jsa-tests-")
os.environ["JOB_SEARCH_DATA_DIR"] = os.path.join(_SANDBOX, "data")
os.environ["JOB_SEARCH_LOG_DIR"] = os.path.join(_SANDBOX, "logs")
# Never read or write the real OS keyring from tests.
os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
os.environ.pop("JOB_SEARCH_API_TOKEN", None)
os.makedirs(os.environ["JOB_SEARCH_DATA_DIR"], exist_ok=True)

import pytest


@pytest.fixture(scope="session", autouse=True)
def _cleanup_sandbox():
    yield
    import shutil

    shutil.rmtree(_SANDBOX, ignore_errors=True)


@pytest.fixture(autouse=True)
def _fresh_database():
    """Every test starts with an empty SQLite database (data is no longer in JSON)."""
    from app.infra import db

    for suffix in ("", "-wal", "-shm"):
        (db.db_path().parent / f"{db.DB_FILE}{suffix}").unlink(missing_ok=True)
    db._migrated_paths.clear()
    yield
