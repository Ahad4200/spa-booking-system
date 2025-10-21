-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (careful in production!)
DROP TABLE IF EXISTS public.spa_bookings CASCADE;
DROP TABLE IF EXISTS public.call_sessions CASCADE;

-- Create spa_bookings table
CREATE TABLE public.spa_bookings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    booking_date DATE NOT NULL,
    slot_start_time TIME NOT NULL,
    slot_end_time TIME NOT NULL,
    booking_reference TEXT UNIQUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    status TEXT DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled', 'completed', 'no-show'))
);

-- Create call_sessions table
CREATE TABLE public.call_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    phone_number TEXT NOT NULL,
    call_id TEXT UNIQUE NOT NULL,
    country TEXT DEFAULT 'IT',
    status TEXT NOT NULL DEFAULT 'in_progress',
    booking_id BIGINT REFERENCES public.spa_bookings(id),
    metadata JSONB,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add comments for documentation
COMMENT ON TABLE public.spa_bookings IS 'Stores all spa session bookings';
COMMENT ON TABLE public.call_sessions IS 'Tracks phone call sessions and links them to bookings';

COMMENT ON COLUMN public.spa_bookings.booking_reference IS 'Unique reference code like SPA-12345';
COMMENT ON COLUMN public.call_sessions.metadata IS 'Additional call data like duration, recording URL, etc';