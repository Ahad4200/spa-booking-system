-- SANTA CATRENA BEAUTY FARM — SPA MANAGEMENT SYSTEM
-- =====================================================
--                    CREATE TABLES
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (careful in production!)
-- DROP TABLE IF EXISTS public.spa_bookings CASCADE;
-- DROP TABLE IF EXISTS public.call_sessions CASCADE;

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

-- =====================================================
--                    CREATE FUNCIONS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to check slot availability
CREATE OR REPLACE FUNCTION public.check_slot_availability(
    p_date DATE,
    p_start_time TIME
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_booking_count INT;
    v_max_capacity INT := 14;  -- From config
BEGIN
    -- Validate inputs
    IF p_date < CURRENT_DATE THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'available', false,
            'message', 'Cannot book slots in the past'
        );
    END IF;
    
    -- Count existing bookings for this slot
    SELECT COUNT(*)
    INTO v_booking_count
    FROM public.spa_bookings
    WHERE booking_date = p_date
      AND slot_start_time = p_start_time
      AND status != 'cancelled';
    
    -- Check if space is available
    IF v_booking_count < v_max_capacity THEN
        RETURN jsonb_build_object(
            'status', 'success',
            'available', true,
            'spots_remaining', v_max_capacity - v_booking_count,
            'total_capacity', v_max_capacity
        );
    ELSE
        RETURN jsonb_build_object(
            'status', 'error',
            'available', false,
            'message', 'Sorry, this time slot is full for this day.',
            'spots_remaining', 0
        );
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', 'An error occurred checking availability',
            'error', SQLERRM
        );
END;
$$;

-- Function to book spa slot
CREATE OR REPLACE FUNCTION public.book_spa_slot(
    p_customer_name TEXT,
    p_customer_phone TEXT,
    p_booking_date DATE,
    p_slot_start_time TIME,
    p_slot_end_time TIME
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_availability_check JSONB;
    v_new_booking_id BIGINT;
    v_booking_reference TEXT;
BEGIN
    -- Input validation
    IF p_customer_name IS NULL OR trim(p_customer_name) = '' THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', 'Customer name is required'
        );
    END IF;
    
    IF p_customer_phone IS NULL OR trim(p_customer_phone) = '' THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', 'Customer phone is required'
        );
    END IF;
    
    -- Check availability first
    v_availability_check := public.check_slot_availability(p_booking_date, p_slot_start_time);
    
    -- If slot is available, create the booking
    IF (v_availability_check->>'available')::boolean = true THEN
        -- Insert booking
        INSERT INTO public.spa_bookings (
            customer_name,
            customer_phone,
            booking_date,
            slot_start_time,
            slot_end_time,
            booking_reference,
            status
        )
        VALUES (
            trim(p_customer_name),
            trim(p_customer_phone),
            p_booking_date,
            p_slot_start_time,
            p_slot_end_time,
            NULL,  -- Will be updated below
            'confirmed'
        )
        RETURNING id INTO v_new_booking_id;
        
        -- Generate booking reference
        v_booking_reference := 'SPA-' || LPAD(v_new_booking_id::TEXT, 6, '0');
        
        -- Update booking with reference
        UPDATE public.spa_bookings
        SET booking_reference = v_booking_reference
        WHERE id = v_new_booking_id;
        
        RETURN jsonb_build_object(
            'status', 'success',
            'message', format('Your spa session is booked for %s from %s to %s.',
                to_char(p_booking_date, 'DD Month YYYY'),
                to_char(p_slot_start_time, 'HH24:MI'),
                to_char(p_slot_end_time, 'HH24:MI')
            ),
            'booking_id', v_new_booking_id,
            'booking_reference', v_booking_reference,
            'details', jsonb_build_object(
                'customer_name', p_customer_name,
                'customer_phone', p_customer_phone,
                'date', p_booking_date,
                'start_time', p_slot_start_time,
                'end_time', p_slot_end_time
            )
        );
    ELSE
        -- Slot is full
        RETURN jsonb_build_object(
            'status', 'error',
            'message', v_availability_check->>'message'
        );
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', 'An error occurred while creating the booking',
            'error', SQLERRM
        );
END;
$$;

-- Function to get daily availability summary
CREATE OR REPLACE FUNCTION public.get_daily_availability(p_date DATE)
RETURNS TABLE (
    slot_start TIME,
    slot_end TIME,
    bookings_count INT,
    spots_available INT,
    is_full BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_max_capacity INT := 14;
BEGIN
    RETURN QUERY
    WITH time_slots AS (
        SELECT 
            '10:00:00'::TIME AS start_time,
            '12:00:00'::TIME AS end_time
        UNION ALL
        SELECT '12:00:00'::TIME, '14:00:00'::TIME
        UNION ALL
        SELECT '14:00:00'::TIME, '16:00:00'::TIME
        UNION ALL
        SELECT '16:00:00'::TIME, '18:00:00'::TIME
        UNION ALL
        SELECT '18:00:00'::TIME, '20:00:00'::TIME
    ),
    booking_counts AS (
        SELECT 
            slot_start_time,
            COUNT(*) as count
        FROM public.spa_bookings
        WHERE booking_date = p_date
          AND status != 'cancelled'
        GROUP BY slot_start_time
    )
    SELECT 
        ts.start_time AS slot_start,
        ts.end_time AS slot_end,
        COALESCE(bc.count, 0)::INT AS bookings_count,
        (v_max_capacity - COALESCE(bc.count, 0))::INT AS spots_available,
        (COALESCE(bc.count, 0) >= v_max_capacity) AS is_full
    FROM time_slots ts
    LEFT JOIN booking_counts bc ON ts.start_time = bc.slot_start_time
    ORDER BY ts.start_time;
END;
$$;

-- =====================================================
--                    CREATE INDEXES
-- =====================================================

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_spa_bookings_date_slot 
ON public.spa_bookings (booking_date, slot_start_time) 
WHERE status != 'cancelled';

CREATE INDEX IF NOT EXISTS idx_spa_bookings_phone 
ON public.spa_bookings (customer_phone);

CREATE INDEX IF NOT EXISTS idx_spa_bookings_reference 
ON public.spa_bookings (booking_reference);

CREATE INDEX IF NOT EXISTS idx_spa_bookings_status 
ON public.spa_bookings (status) 
WHERE status = 'confirmed';

CREATE INDEX IF NOT EXISTS idx_call_sessions_call_id 
ON public.call_sessions (call_id);

CREATE INDEX IF NOT EXISTS idx_call_sessions_phone 
ON public.call_sessions (phone_number);

CREATE INDEX IF NOT EXISTS idx_call_sessions_booking 
ON public.call_sessions (booking_id) 
WHERE booking_id IS NOT NULL;

-- Create triggers for updated_at
CREATE TRIGGER update_spa_bookings_timestamp
BEFORE UPDATE ON public.spa_bookings
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_call_sessions_timestamp
BEFORE UPDATE ON public.call_sessions
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Add constraints
ALTER TABLE public.spa_bookings
ADD CONSTRAINT chk_spa_booking_times 
CHECK (slot_start_time < slot_end_time);

ALTER TABLE public.spa_bookings
ADD CONSTRAINT chk_spa_booking_date 
CHECK (booking_date >= CURRENT_DATE);

-- Create composite unique constraint to prevent double bookings
ALTER TABLE public.spa_bookings
ADD CONSTRAINT unq_customer_slot 
UNIQUE (customer_phone, booking_date, slot_start_time);

-- =====================================================
--                    SEED DATA
-- =====================================================

-- Seed data for testing the spa booking system
-- This creates sample bookings for development and testing

-- Clear existing test data (be careful in production!)
DELETE FROM public.spa_bookings WHERE customer_name LIKE 'Test%';
DELETE FROM public.call_sessions WHERE phone_number LIKE '%999%';

-- Insert test bookings for today
INSERT INTO public.spa_bookings (
    customer_name,
    customer_phone,
    booking_date,
    slot_start_time,
    slot_end_time,
    booking_reference,
    status,
    notes
) VALUES
    -- Morning slots (10:00 - 12:00) - 10 bookings
    ('Test Customer 1', '+39 333 111 0001', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST01', 'confirmed', 'Test booking'),
    ('Mario Rossi', '+39 333 222 0002', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST02', 'confirmed', NULL),
    ('Luigi Bianchi', '+39 333 333 0003', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST03', 'confirmed', NULL),
    ('Anna Verdi', '+39 333 444 0004', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST04', 'confirmed', NULL),
    ('Giulia Romano', '+39 333 555 0005', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST05', 'confirmed', NULL),
    ('Marco Ferri', '+39 333 666 0006', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST06', 'confirmed', NULL),
    ('Sara Costa', '+39 333 777 0007', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST07', 'confirmed', NULL),
    ('Paolo Conti', '+39 333 888 0008', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST08', 'confirmed', NULL),
    ('Laura Gallo', '+39 333 999 0009', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST09', 'confirmed', NULL),
    ('Roberto Bruno', '+39 333 111 0010', CURRENT_DATE, '10:00:00', '12:00:00', 'SPA-TEST10', 'confirmed', NULL),
    
    -- Afternoon slot (14:00 - 16:00) - 5 bookings (plenty of space)
    ('Francesca Russo', '+39 333 111 0011', CURRENT_DATE, '14:00:00', '16:00:00', 'SPA-TEST11', 'confirmed', NULL),
    ('Giovanni Marino', '+39 333 222 0012', CURRENT_DATE, '14:00:00', '16:00:00', 'SPA-TEST12', 'confirmed', NULL),
    ('Chiara Greco', '+39 333 333 0013', CURRENT_DATE, '14:00:00', '16:00:00', 'SPA-TEST13', 'confirmed', NULL),
    ('Alessandro Rota', '+39 333 444 0014', CURRENT_DATE, '14:00:00', '16:00:00', 'SPA-TEST14', 'confirmed', NULL),
    ('Martina Serra', '+39 333 555 0015', CURRENT_DATE, '14:00:00', '16:00:00', 'SPA-TEST15', 'confirmed', NULL),
    
    -- Evening slot (18:00 - 20:00) - 14 bookings (fully booked)
    ('Luca Fontana', '+39 333 111 0016', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST16', 'confirmed', 'Group booking'),
    ('Elena Rizzi', '+39 333 222 0017', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST17', 'confirmed', 'Group booking'),
    ('Davide Colombo', '+39 333 333 0018', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST18', 'confirmed', NULL),
    ('Silvia Mazza', '+39 333 444 0019', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST19', 'confirmed', NULL),
    ('Andrea Barbieri', '+39 333 555 0020', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST20', 'confirmed', NULL),
    ('Federica Lombardi', '+39 333 666 0021', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST21', 'confirmed', NULL),
    ('Matteo Moretti', '+39 333 777 0022', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST22', 'confirmed', NULL),
    ('Valentina Ricci', '+39 333 888 0023', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST23', 'confirmed', NULL),
    ('Simone Gatti', '+39 333 999 0024', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST24', 'confirmed', NULL),
    ('Alice Ferrari', '+39 333 111 0025', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST25', 'confirmed', NULL),
    ('Stefano Villa', '+39 333 222 0026', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST26', 'confirmed', NULL),
    ('Giorgia Leone', '+39 333 333 0027', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST27', 'confirmed', NULL),
    ('Riccardo Sala', '+39 333 444 0028', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST28', 'confirmed', NULL),
    ('Beatrice Conte', '+39 333 555 0029', CURRENT_DATE, '18:00:00', '20:00:00', 'SPA-TEST29', 'confirmed', NULL);

-- Insert bookings for tomorrow (lighter schedule)
INSERT INTO public.spa_bookings (
    customer_name,
    customer_phone,
    booking_date,
    slot_start_time,
    slot_end_time,
    booking_reference,
    status
) VALUES
    ('Tommaso Bassi', '+39 333 666 0030', CURRENT_DATE + INTERVAL '1 day', '10:00:00', '12:00:00', 'SPA-TEST30', 'confirmed'),
    ('Carla Monti', '+39 333 777 0031', CURRENT_DATE + INTERVAL '1 day', '10:00:00', '12:00:00', 'SPA-TEST31', 'confirmed'),
    ('Nicola Piras', '+39 333 888 0032', CURRENT_DATE + INTERVAL '1 day', '12:00:00', '14:00:00', 'SPA-TEST32', 'confirmed'),
    ('Monica Caruso', '+39 333 999 0033', CURRENT_DATE + INTERVAL '1 day', '14:00:00', '16:00:00', 'SPA-TEST33', 'confirmed'),
    ('Fabio Santoro', '+39 333 111 0034', CURRENT_DATE + INTERVAL '1 day', '16:00:00', '18:00:00', 'SPA-TEST34', 'confirmed');

-- Insert some cancelled bookings for testing
INSERT INTO public.spa_bookings (
    customer_name,
    customer_phone,
    booking_date,
    slot_start_time,
    slot_end_time,
    booking_reference,
    status,
    notes
) VALUES
    ('Cancelled Customer 1', '+39 333 999 9991', CURRENT_DATE, '12:00:00', '14:00:00', 'SPA-CANCEL1', 'cancelled', 'Customer cancelled'),
    ('Cancelled Customer 2', '+39 333 999 9992', CURRENT_DATE, '16:00:00', '18:00:00', 'SPA-CANCEL2', 'cancelled', 'No show');

-- Insert test call sessions
INSERT INTO public.call_sessions (
    phone_number,
    call_id,
    country,
    status,
    booking_id,
    metadata
) VALUES
    ('+39 333 111 0001', 'CALL-TEST-001', 'IT', 'completed', 1, '{"duration": 120, "language": "italian"}'),
    ('+39 333 222 0002', 'CALL-TEST-002', 'IT', 'completed', 2, '{"duration": 95, "language": "italian"}'),
    ('+39 333 999 9999', 'CALL-TEST-003', 'IT', 'abandoned', NULL, '{"duration": 15, "reason": "hung_up"}');

-- Create a summary view for testing
CREATE OR REPLACE VIEW booking_summary AS
SELECT 
    booking_date,
    slot_start_time,
    slot_end_time,
    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed_count,
    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_count,
    14 - COUNT(*) FILTER (WHERE status = 'confirmed') as spots_available,
    ARRAY_AGG(customer_name ORDER BY customer_name) FILTER (WHERE status = 'confirmed') as customer_names
FROM public.spa_bookings
GROUP BY booking_date, slot_start_time, slot_end_time
ORDER BY booking_date, slot_start_time;

-- Verify the test data
SELECT 
    booking_date,
    slot_start_time || ' - ' || slot_end_time as time_slot,
    confirmed_count as bookings,
    spots_available,
    CASE 
        WHEN spots_available = 0 THEN 'FULLY BOOKED'
        WHEN spots_available <= 3 THEN 'Almost Full'
        ELSE 'Available'
    END as status
FROM booking_summary
WHERE booking_date >= CURRENT_DATE
ORDER BY booking_date, slot_start_time;

-- Show statistics
SELECT 
    'Total Bookings' as metric,
    COUNT(*) as value
FROM public.spa_bookings
WHERE status = 'confirmed'
UNION ALL
SELECT 
    'Today Bookings',
    COUNT(*)
FROM public.spa_bookings
WHERE booking_date = CURRENT_DATE AND status = 'confirmed'
UNION ALL
SELECT 
    'Cancelled Bookings',
    COUNT(*)
FROM public.spa_bookings
WHERE status = 'cancelled';