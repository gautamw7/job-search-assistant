"""Entry for PyInstaller sidecar: `job-search-api --host 127.0.0.1 --port 8000`."""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("app.app:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
