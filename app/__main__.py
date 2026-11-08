"""Entry for PyInstaller sidecar: `job-search-api --host 127.0.0.1 --port 8000`."""

import argparse

import uvicorn

# Static import (not a "app.app:app" string) so PyInstaller bundles the app
# and the frozen sidecar does not fail with "No module named 'app'".
from app.app import app
from app.core.process import start_parent_watchdog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    start_parent_watchdog()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
