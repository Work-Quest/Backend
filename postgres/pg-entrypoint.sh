#!/bin/sh
set -eu

# If DATABASE_URL is present, derive POSTGRES_* from it so the container can init itself correctly.
# Example: postgres://postgres:postgres@postgres:5432/workquest
if [ "${DATABASE_URL:-}" != "" ]; then
  eval "$(
    python3 - <<'PY'
import os
from urllib.parse import urlparse

u = urlparse(os.environ["DATABASE_URL"])
if u.scheme not in ("postgres", "postgresql"):
    raise SystemExit(f"Unsupported DATABASE_URL scheme: {u.scheme}")

db = (u.path or "").lstrip("/")
user = u.username or ""
pw = u.password or ""

def sh_escape(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"

if user:
    print(f"export POSTGRES_USER={sh_escape(user)}")
if pw:
    print(f"export POSTGRES_PASSWORD={sh_escape(pw)}")
if db:
    print(f"export POSTGRES_DB={sh_escape(db)}")
PY
  )"
fi

# Hand off to the official Postgres entrypoint
exec /usr/local/bin/docker-entrypoint.sh "$@"

