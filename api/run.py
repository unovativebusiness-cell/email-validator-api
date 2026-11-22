"""Load .env and start the email verification API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(ROOT / ".env")


def main() -> None:
    if not os.environ.get("EMAIL_API_SECRET", "").strip():
        raise SystemExit(
            "EMAIL_API_SECRET is not set. Copy api/.env.example to api/.env and set a secret."
        )

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    # Import after env + path are ready so EMAIL_API_SECRET is visible to the app module.
    from api.app import app

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
