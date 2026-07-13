#!/usr/bin/env python3
"""Fix inconsistent migration history by recording missing migrations."""
import os
import sys
import urllib.parse
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL, skipping migration fix")
    sys.exit(0)

import psycopg

url = urllib.parse.urlparse(DATABASE_URL)
conn = psycopg.connect(
    dbname=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port,
    sslmode="require"
)
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
