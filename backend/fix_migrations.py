#!/usr/bin/env python3
"""
Fix migration history and schema for a database created outside Django.

1. Clear ALL migration records from django_migrations.
2. Fake-apply ALL migrations (mark as applied without running SQL).
3. Add any missing columns/tables via raw SQL (IF NOT EXISTS).
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

print("Adding missing columns and tables via SQL...")
conn = psycopg.connect(**db_params)
conn.autocommit = True

SQL_FIXES = [
    # ═══════════════════════════════════════════════════════════
    # TABLES THAT MAY NOT EXIST
    # ═══════════════════════════════════════════════════════════
    '''CREATE TABLE IF NOT EXISTS merchant_tables (
        id bigserial PRIMARY KEY,
        merchant_id bigint NOT NULL REFERENCES merchant_profiles(id),
        name varchar(100) NOT NULL DEFAULT '',
        table_number integer NOT NULL DEFAULT 0,
        public_token varchar(64) UNIQUE NOT NULL DEFAULT '',
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamp with time zone NOT NULL DEFAULT now(),
        updated_at timestamp with time zone NOT NULL DEFAULT now()
    )''',
    '''CREATE TABLE IF NOT EXISTS membership_qr_tokens (
        id bigserial PRIMARY KEY,
        membership_id bigint NOT NULL REFERENCES customer_merchant_profiles(id),
        public_token varchar(64) UNIQUE NOT NULL DEFAULT '',
        token_version integer NOT NULL DEFAULT 1,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamp with time zone NOT NULL DEFAULT now(),
        rotated_at timestamp with time zone
    )''',
    '''CREATE TABLE IF NOT EXISTS merchant_card_designs (
        id bigserial PRIMARY KEY,
        merchant_id bigint NOT NULL UNIQUE REFERENCES merchant_profiles(id),
        card_title varchar(100) NOT NULL DEFAULT 'Membership',
        card_subtitle varchar(200) NOT NULL DEFAULT '',
        background_type varchar(20) NOT NULL DEFAULT 'solid',
        primary_color varchar(7) NOT NULL DEFAULT '#171717',
        secondary_color varchar(7) NOT NULL DEFAULT '#382418',
        accent_color varchar(7) NOT NULL DEFAULT '#D97941',
        text_mode varchar(10) NOT NULL DEFAULT 'light',
        background_image varchar(200) NOT NULL DEFAULT '',
        background_pattern varchar(30) NOT NULL DEFAULT 'zentro_dots',
        logo varchar(200) NOT NULL DEFAULT '',
        tier_style varchar(20) NOT NULL DEFAULT 'default',
        points_label varchar(50) NOT NULL DEFAULT 'POINTS',
        membership_label varchar(50) NOT NULL DEFAULT 'MEMBERSHIP',
        show_lifetime_points boolean NOT NULL DEFAULT true,
        show_joined_date boolean NOT NULL DEFAULT true,
        show_qr_shortcut boolean NOT NULL DEFAULT true,
        is_published boolean NOT NULL DEFAULT false,
        created_at timestamp with time zone NOT NULL DEFAULT now(),
        updated_at timestamp with time zone NOT NULL DEFAULT now()
    )''',
    '''CREATE TABLE IF NOT EXISTS notifications (
        id bigserial PRIMARY KEY,
        user_id bigint NOT NULL REFERENCES users(id),
        title varchar(255) NOT NULL DEFAULT '',
        message text NOT NULL DEFAULT '',
        notification_type varchar(30) NOT NULL DEFAULT 'generic',
        merchant_name varchar(255) NOT NULL DEFAULT '',
        context_url varchar(500) NOT NULL DEFAULT '',
        order_id integer,
        merchant_id integer,
        reward_id integer,
        is_read boolean NOT NULL DEFAULT false,
        created_at timestamp with time zone NOT NULL DEFAULT now()
    )''',
    '''CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id bigserial PRIMARY KEY,
        user_id bigint NOT NULL REFERENCES users(id),
        token varchar(64) UNIQUE NOT NULL DEFAULT '',
        created_at timestamp with time zone NOT NULL DEFAULT now(),
        used boolean NOT NULL DEFAULT false
    )''',

    # ═══════════════════════════════════════════════════════════
    # customer_profiles
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE customer_profiles ADD COLUMN IF NOT EXISTS transfer_code varchar(8) UNIQUE",

    # ═══════════════════════════════════════════════════════════
    # merchant_profiles
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS onboarding_complete boolean DEFAULT false",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS latitude numeric(9,6)",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS longitude numeric(9,6)",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS qr_code text DEFAULT ''",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS store_theme_color varchar(7) DEFAULT ''",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS table_ordering_enabled boolean DEFAULT false",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS allow_pickup boolean DEFAULT true",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS allow_delivery boolean DEFAULT false",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS allow_dine_in boolean DEFAULT false",
    "ALTER TABLE merchant_profiles ADD COLUMN IF NOT EXISTS allow_point_transfer boolean DEFAULT false",

    # ═══════════════════════════════════════════════════════════
    # customer_merchant_profiles
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE customer_merchant_profiles ADD COLUMN IF NOT EXISTS membership_number varchar(20) UNIQUE",
    "ALTER TABLE customer_merchant_profiles ADD COLUMN IF NOT EXISTS last_active_at timestamp with time zone",
    "ALTER TABLE customer_merchant_profiles ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true",

    # ═══════════════════════════════════════════════════════════
    # customer_merchant_wallets
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE customer_merchant_wallets ADD COLUMN IF NOT EXISTS membership_id bigint REFERENCES customer_merchant_profiles(id)",
    "ALTER TABLE customer_merchant_wallets ADD COLUMN IF NOT EXISTS redeemed_points integer DEFAULT 0",

    # ═══════════════════════════════════════════════════════════
    # point_transactions
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE point_transactions ADD COLUMN IF NOT EXISTS membership_id bigint REFERENCES customer_merchant_profiles(id)",
    "ALTER TABLE point_transactions ADD COLUMN IF NOT EXISTS transfer_group uuid",

    # ═══════════════════════════════════════════════════════════
    # merchant_punch_cards
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE merchant_punch_cards ADD COLUMN IF NOT EXISTS stamp_gif_url varchar(200) DEFAULT ''",

    # ═══════════════════════════════════════════════════════════
    # customer_punch_cards
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE customer_punch_cards ADD COLUMN IF NOT EXISTS proof_code varchar(10) DEFAULT ''",
    "ALTER TABLE customer_punch_cards ADD COLUMN IF NOT EXISTS proof_code_expires_at timestamp with time zone",
    "ALTER TABLE customer_punch_cards ADD COLUMN IF NOT EXISTS proof_code_used boolean DEFAULT false",

    # ═══════════════════════════════════════════════════════════
    # orders
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS loyalty_awarded boolean DEFAULT false",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_type varchar(30) DEFAULT 'regular'",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS fulfillment_type varchar(20) DEFAULT 'pickup'",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS table_id bigint REFERENCES merchant_tables(id)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS table_name_snapshot varchar(100) DEFAULT ''",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS table_number_snapshot integer",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancellation_reason varchar(50) DEFAULT ''",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancelled_by varchar(20) DEFAULT ''",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS punch_card_redemption_id bigint REFERENCES customer_punch_cards(id)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS reward_redemption_id bigint REFERENCES redemptions(id)",

    # ═══════════════════════════════════════════════════════════
    # redemptions
    # ═══════════════════════════════════════════════════════════
    "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS cancel_requested boolean DEFAULT false",
    "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS cancel_reason text DEFAULT ''",
    "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS cancel_proof_url text DEFAULT ''",
    "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS merchant_response text DEFAULT ''",
    "ALTER TABLE redemptions ADD COLUMN IF NOT EXISTS resolved_at timestamp with time zone",
]

with conn.cursor() as cur:
    for sql in SQL_FIXES:
        try:
            cur.execute(sql)
            print(f"  OK: {sql[:70]}...")
        except Exception as e:
            print(f"  SKIP: {sql[:70]}... -> {e}")

conn.close()
print("\nSchema fix complete!")
