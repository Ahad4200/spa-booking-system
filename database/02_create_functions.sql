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