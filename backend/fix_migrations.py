#!/usr/bin/env python3
"""
Reset and fix migration history.

1. Delete all migration records for custom apps (tables were created manually in Supabase).
2. Run `manage.py migrate --fake-initial`:
   - fakes CreateModel (tables already exist)
   - actually runs AddField / AlterField (adds missing columns)
"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    import urllib.parse
    url = urllib.parse.urlparse(DATABASE_URL)
    db_params = {
        "dbname": url.path[1:],
        "user": url.username or "",
        "password": url.password or "",
        "host": url.hostname or "localhost",
        "port": url.port or 5432,
        "sslmode": "require",
    }
elif os.environ.get("DB_ENGINE") == "django.db.backends.postgresql":
    db_params = {
        "dbname": os.environ.get("DB_NAME", "zentro"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "sslmode": os.environ.get("DB_SSLMODE", "prefer"),
    }
else:
    print("No database config found, skipping migration fix")
    sys.exit(0)

import psycopg

CUSTOM_APPS = ["loyalty", "accounts", "orders", "merchants", "notifications"]

conn = psycopg.connect(**db_params)
conn.autocommit = True

with conn.cursor() as cur:
    for app in CUSTOM_APPS:
        cur.execute("DELETE FROM django_migrations WHERE app = %s", (app,))
        print(f"Cleared migration records for {app}")

conn.close()
print("Database cleaned. Running migrate --fake-initial ...")

result = subprocess.run(
    [sys.executable, os.path.join(BASE_DIR, "manage.py"), "migrate", "--fake-initial", "--no-input"],
    cwd=BASE_DIR,
)

if result.returncode != 0:
    print(f"migrate --fake-initial failed with code {result.returncode}")
    sys.exit(result.returncode)

print("Migration fix complete")
