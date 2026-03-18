#!/usr/bin/env python3
"""Tool Hub API startup script."""

import os

import uvicorn


def main() -> None:
    os.environ.setdefault("LOG_LEVEL", "INFO")
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
