-- Migration: Create merchant_profiles table
-- This table stores merchant-specific data separate from the customer profiles table

-- Add role column to profiles if not exists
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS role text DEFAULT 'customer' CHECK (role IN ('customer', 'merchant'));

-- Create merchant_profiles table
CREATE TABLE IF NOT EXISTS merchant_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  store_name text NOT NULL,
  store_slug text UNIQUE,
  business_type text,
  address text,
  phone text,
  logo_url text,
  banner_url text,
  description text,
  is_approved boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE merchant_profiles ENABLE ROW LEVEL SECURITY;

-- Merchant can read their own profile
CREATE POLICY "Merchants can read own profile"
  ON merchant_profiles
  FOR SELECT
  USING (auth.uid() = user_id);

-- Merchant can update their own profile
CREATE POLICY "Merchants can update own profile"
  ON merchant_profiles
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Insert policy: authenticated users can create their own merchant profile
CREATE POLICY "Authenticated users can create merchant profile"
  ON merchant_profiles
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_merchant_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_merchant_profiles_updated_at ON merchant_profiles;
CREATE TRIGGER set_merchant_profiles_updated_at
  BEFORE UPDATE ON merchant_profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_merchant_profiles_updated_at();

-- Auto-create merchant profile on signup when role is merchant
CREATE OR REPLACE FUNCTION handle_new_merchant()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.raw_user_meta_data->>'role' = 'merchant' THEN
    INSERT INTO merchant_profiles (user_id, store_name, store_slug)
    VALUES (
      NEW.id,
      COALESCE(NEW.raw_user_meta_data->>'store_name', 'My Store'),
      LOWER(REGEXP_REPLACE(
        COALESCE(NEW.raw_user_meta_data->>'store_name', 'my-store'),
        '[^a-z0-9]+', '-', 'gi'
      ))
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if any
DROP TRIGGER IF EXISTS on_auth_user_created_merchant ON auth.users;

-- Create trigger on auth.users
CREATE TRIGGER on_auth_user_created_merchant
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_merchant();

-- Create index on user_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_merchant_profiles_user_id ON merchant_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_merchant_profiles_store_slug ON merchant_profiles(store_slug);
