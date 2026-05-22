"""Verify .env shape and Neon connectivity (does not print secrets)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
env_path = ROOT / ".env"
if not env_path.exists():
    print("ERROR: .env not found")
    sys.exit(1)

for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def ok(label: str, passed: bool) -> None:
    print(f"{label}: {'OK' if passed else 'FIX'}")


url = os.environ.get("DATABASE_URL", "")
parsed = urlparse(url)
ok("DATABASE_URL set", bool(url))
ok("DATABASE_URL is postgresql URI", url.startswith(("postgresql://", "postgres://")))
ok("DATABASE_URL has host", bool(parsed.hostname))
ok("DATABASE_URL has user", bool(parsed.username))
ok("DATABASE_URL has password", bool(parsed.password))
ok("DATABASE_URL has database name", bool(parsed.path and len(parsed.path) > 1))
ok("DATABASE_URL has sslmode", "sslmode=require" in url)

smtp_pw = os.environ.get("SMTP_PASSWORD", "")
ok("ALERT_EMAIL_TO set", bool(os.environ.get("ALERT_EMAIL_TO")))
ok("ALERT_EMAIL_FROM set", bool(os.environ.get("ALERT_EMAIL_FROM")))
ok("SMTP_HOST set", bool(os.environ.get("SMTP_HOST")))
ok("SMTP_PORT set", bool(os.environ.get("SMTP_PORT")))
ok("SMTP_USER set", bool(os.environ.get("SMTP_USER")))
ok("SMTP_PASSWORD set", bool(smtp_pw))
ok("SMTP_PASSWORD has no spaces", " " not in smtp_pw)

try:
    import psycopg

    with psycopg.connect(url, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    print("Neon connect: OK")
except ImportError:
    print("Neon connect: SKIP (pip install psycopg[binary])")
    sys.exit(0)
except Exception as e:
    print(f"Neon connect: FAIL ({type(e).__name__})")
    sys.exit(1)

# Optional SMTP test only if --smtp flag
if "--smtp" in sys.argv:
    import smtplib

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pw = os.environ["SMTP_PASSWORD"].replace(" ", "")
    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(user, pw)
        print("Gmail SMTP login: OK")
    except Exception as e:
        print(f"Gmail SMTP login: FAIL ({type(e).__name__})")
        sys.exit(1)
