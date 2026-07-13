#!/usr/bin/env python3
"""Fix inconsistent migration history by recording missing migrations."""
import os
import sys
from datetime import datetime, timezone

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

conn = psycopg.connect(**db_params)
conn.autocommit = True

migrations = [
    ("loyalty", "0011_remove_merchantpunchcard_linked_menu_item_and_more"),
    ("loyalty", "0012_pointtransaction_transfer_group"),
]

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f%z")

with conn.cursor() as cur:
    for app, name in migrations:
        cur.execute(
            "INSERT INTO django_migrations (app, name, applied) SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = %s AND name = %s)",
            (app, name, now, app, name)
        )
        print(f"Ensured {app}.{name} is recorded")

conn.close()
print("Migration fix complete")
