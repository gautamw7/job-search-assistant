import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def backup_restore_user_communication():
    """Backup user communication style before test and restore after test."""
    path = "data/user_communication_style.json"
    backup_data = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                backup_data = f.read()
        except Exception:
            pass

    yield

    if backup_data is not None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(backup_data)
    elif os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
