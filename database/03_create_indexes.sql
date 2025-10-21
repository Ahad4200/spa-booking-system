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