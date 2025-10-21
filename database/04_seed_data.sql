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