#!/usr/bin/env python3
"""Fix inconsistent migration history by recording ALL missing migrations."""
import os
import re
import sys
from datetime import datetime, timezone, timedelta

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MIGRATION_RE = re.compile(r"^(\d{4})_.*\.py$")

APP_DIRS = ["loyalty", "accounts", "orders", "merchants", "notifications"]

def discover_migrations():
    found = []
    for app in APP_DIRS:
        mig_dir = os.path.join(BASE_DIR, app, "migrations")
        if not os.path.isdir(mig_dir):
            continue
        for fname in os.listdir(mig_dir):
            m = MIGRATION_RE.match(fname)
            if m:
                name = fname[:-3]
                found.append((app, name))
    found.sort(key=lambda x: (x[0], x[1]))
    return found

all_migrations = discover_migrations()
print(f"Discovered {len(all_migrations)} migration files on disk")

conn = psycopg.connect(**db_params)
conn.autocommit = True

with conn.cursor() as cur:
    cur.execute("SELECT app, name, applied FROM django_migrations ORDER BY app, applied")
    existing = {}
    for row in cur.fetchall():
        app, name, applied = row
        if app not in existing:
            existing[app] = []
        existing[app].append((name, applied))
    print(f"Found {sum(len(v) for v in existing.values())} migrations already recorded")

    inserted = 0
    for app, name in all_migrations:
        app_existing = existing.get(app, [])
        app_names = [n for n, _ in app_existing]

        if name in app_names:
            continue

        if app_existing:
            earliest_applied = min(a for _, a in app_existing)
            idx = sum(1 for n, _ in app_existing if n < name)
            ts = earliest_applied - timedelta(seconds=(idx + 1))
        else:
            ts = datetime(2024, 1, 1, tzinfo=timezone.utc)

        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S.%f%z")
        cur.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
            (app, name, ts_str)
        )
        print(f"Inserted {app}.{name} (applied={ts_str})")
        inserted += 1

    print(f"Inserted {inserted} missing migrations total")

conn.close()
print("Migration fix complete")
