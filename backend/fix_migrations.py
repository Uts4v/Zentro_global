#!/usr/bin/env python3
"""
Fix migration history for a database created outside Django.

1. Clear ALL migration records from django_migrations.
2. Fake-apply ALL migrations (mark as applied without running SQL).
3. Add any missing columns via raw SQL (IF NOT EXISTS).
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

conn = psycopg.connect(**db_params)
conn.autocommit = True

with conn.cursor() as cur:
    cur.execute("DELETE FROM django_migrations")
    print("Cleared ALL migration records")

conn.close()

print("Faking ALL migrations...")
result = subprocess.run(
    [sys.executable, os.path.join(BASE_DIR, "manage.py"), "migrate", "--fake", "--no-input"],
    cwd=BASE_DIR,
)
if result.returncode != 0:
    print(f"migrate --fake failed with code {result.returncode}")
    sys.exit(result.returncode)

print("Adding missing columns via SQL...")
conn = psycopg.connect(**db_params)
conn.autocommit = True

SQL_FIXES = [
    # accounts
    'ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS transfer_code varchar(8)',
    # loyalty - redemption fields
    'ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS cancel_requested boolean DEFAULT false',
    'ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS cancel_reason text',
    'ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS cancel_proof_url text',
    'ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS merchant_response text',
    'ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS resolved_at timestamp with time zone',
    # loyalty - point transactions
    'ALTER TABLE point_transactions ADD COLUMN IF NOT EXISTS transfer_group_id integer',
    # loyalty - punch cards
    'ALTER TABLE merchant_punch_cards ADD COLUMN IF NOT EXISTS linked_menu_item_id integer',
    'ALTER TABLE merchant_punch_cards ADD COLUMN IF NOT EXISTS auto_generate_stamps boolean DEFAULT true',
    'ALTER TABLE customer_punch_cards ADD COLUMN IF NOT EXISTS current_count integer DEFAULT 0',
    # loyalty - stamp/loyalty card
    'ALTER TABLE merchant_punch_cards ADD COLUMN IF NOT EXISTS stamp_gif_url text',
    # loyalty - membership fields
    'ALTER TABLE customer_merchant_wallets ADD COLUMN IF NOT EXISTS membership_id integer',
    'ALTER TABLE customer_merchant_wallets ADD COLUMN IF NOT EXISTS membership_joined_at timestamp with time zone',
    # orders - fulfillment
    'ALTER TABLE orders ADD COLUMN IF NOT EXISTS fulfillment_type varchar(20) DEFAULT \'dine_in\'',
    'ALTER TABLE orders ADD COLUMN IF NOT EXISTS table_number varchar(10)',
    'ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_address text',
    # merchants - store theme
    'ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS store_theme_color varchar(7) DEFAULT \'#6366f1\'',
    'ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS allow_delivery boolean DEFAULT false',
    'ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS delivery_fee integer DEFAULT 0',
    'ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS delivery_radius_km integer DEFAULT 0',
    'ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS allow_point_transfer boolean DEFAULT false',
    # notifications table (if not exists from Supabase)
    '''CREATE TABLE IF NOT EXISTS notifications (
        id bigserial PRIMARY KEY,
        user_id bigint NOT NULL REFERENCES users(id),
        title varchar(255) NOT NULL DEFAULT '',
        message text NOT NULL DEFAULT '',
        notification_type varchar(30) NOT NULL DEFAULT 'general',
        is_read boolean NOT NULL DEFAULT false,
        created_at timestamp with time zone NOT NULL DEFAULT now()
    )''',
    # orders - reward/redemption
    'ALTER TABLE orders ADD COLUMN IF NOT EXISTS reward_redemption_id integer',
    'ALTER TABLE orders ADD COLUMN IF NOT EXISTS source_punch_card_id integer',
    'ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_reward_order boolean DEFAULT false',
]

with conn.cursor() as cur:
    for sql in SQL_FIXES:
        try:
            cur.execute(sql)
            col = sql.split("ADD COLUMN IF NOT EXISTS ")[-1].split(" ")[0] if "ADD COLUMN" in sql else "table"
            print(f"  OK: {sql[:60]}...")
        except Exception as e:
            print(f"  SKIP: {sql[:60]}... -> {e}")

conn.close()
print("Schema fix complete")
