-- Test Data for Bidding System
-- Run this after your backend creates the tables

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- INSERT TEST USERS
-- ============================================

-- Admin User (password: admin123)
-- Bcrypt hash of 'admin123': $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO
INSERT INTO users (id, username, email, password, is_admin, weight, created_at, updated_at) VALUES
(uuid_generate_v4(), 'admin', 'admin@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', TRUE, 5.0, NOW(), NOW());

-- Regular Users (password: test123 for all)
-- Different weights to test scoring formula
INSERT INTO users (id, username, email, password, is_admin, weight, created_at, updated_at) VALUES
(uuid_generate_v4(), 'user1', 'user1@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.0, NOW(), NOW()),
(uuid_generate_v4(), 'user2', 'user2@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.5, NOW(), NOW()),
(uuid_generate_v4(), 'user3', 'user3@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 2.0, NOW(), NOW()),
(uuid_generate_v4(), 'user4', 'user4@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 0.8, NOW(), NOW()),
(uuid_generate_v4(), 'user5', 'user5@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.2, NOW(), NOW()),
(uuid_generate_v4(), 'user6', 'user6@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.8, NOW(), NOW()),
(uuid_generate_v4(), 'user7', 'user7@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.3, NOW(), NOW()),
(uuid_generate_v4(), 'user8', 'user8@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.1, NOW(), NOW()),
(uuid_generate_v4(), 'user9', 'user9@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.6, NOW(), NOW()),
(uuid_generate_v4(), 'user10', 'user10@bidding.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqXfj4WZdO', FALSE, 1.4, NOW(), NOW());

-- ============================================
-- INSERT TEST PRODUCTS
-- ============================================

-- Get admin user ID
DO $$
DECLARE
    admin_user_id UUID;
BEGIN
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    
    -- Insert Products
    INSERT INTO bidding_products (id, name, description, admin_id, created_at, updated_at) VALUES
    (
        uuid_generate_v4(), 
        'Limited Edition Sneakers',
        'Nike Air Jordan 1 Retro High - Limited Release with exclusive colorway. Only 5 pairs available worldwide.',
        admin_user_id,
        NOW(),
        NOW()
    ),
    (
        uuid_generate_v4(),
        'RTX 4090 Graphics Card',
        'NVIDIA GeForce RTX 4090 24GB GDDR6X - The ultimate graphics card for gaming and AI workloads.',
        admin_user_id,
        NOW(),
        NOW()
    ),
    (
        uuid_generate_v4(),
        'Concert VIP Tickets',
        'Taylor Swift Eras Tour - Front Row VIP Experience with meet and greet. 10 tickets available.',
        admin_user_id,
        NOW(),
        NOW()
    ),
    (
        uuid_generate_v4(),
        'Limited Rolex Watch',
        'Rolex Submariner Date - Stainless steel with blue dial. Rare vintage model from 1980s.',
        admin_user_id,
        NOW(),
        NOW()
    ),
    (
        uuid_generate_v4(),
        'Gaming Console Bundle',
        'PlayStation 5 Pro with 5 exclusive games and extra controller. Limited edition design.',
        admin_user_id,
        NOW(),
        NOW()
    );
END $$;

-- ============================================
-- INSERT TEST BIDDING SESSIONS
-- ============================================

DO $$
DECLARE
    admin_user_id UUID;
    sneakers_id UUID;
    rtx_id UUID;
    concert_id UUID;
    rolex_id UUID;
    ps5_id UUID;
BEGIN
    -- Get IDs
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    SELECT id INTO sneakers_id FROM bidding_products WHERE name LIKE '%Sneakers%';
    SELECT id INTO rtx_id FROM bidding_products WHERE name LIKE '%RTX%';
    SELECT id INTO concert_id FROM bidding_products WHERE name LIKE '%Concert%';
    SELECT id INTO rolex_id FROM bidding_products WHERE name LIKE '%Rolex%';
    SELECT id INTO ps5_id FROM bidding_products WHERE name LIKE '%Gaming Console%';
    
    -- Insert Bidding Sessions
    -- Session 1: Sneakers (Active, short duration)
    INSERT INTO bidding_sessions (
        id, admin_id, product_id, upset_price, final_price, inventory,
        alpha, beta, gamma, start_time, end_time, duration, is_active,
        created_at, updated_at
    ) VALUES (
        uuid_generate_v4(),
        admin_user_id,
        sneakers_id,
        200.0,  -- upset_price (starting bid)
        NULL,   -- final_price (not finished yet)
        5,      -- inventory
        0.5,    -- alpha
        1000.0, -- beta
        2.0,    -- gamma
        NOW() - INTERVAL '5 minutes',  -- started 5 minutes ago
        NOW() + INTERVAL '10 minutes', -- ends in 10 minutes
        INTERVAL '15 minutes',
        TRUE,   -- is_active
        NOW(),
        NOW()
    );
    
    -- Session 2: RTX 4090 (Active, medium duration)
    INSERT INTO bidding_sessions (
        id, admin_id, product_id, upset_price, final_price, inventory,
        alpha, beta, gamma, start_time, end_time, duration, is_active,
        created_at, updated_at
    ) VALUES (
        uuid_generate_v4(),
        admin_user_id,
        rtx_id,
        1599.0,
        NULL,
        3,
        0.6,
        800.0,
        1.5,
        NOW() - INTERVAL '2 minutes',
        NOW() + INTERVAL '30 minutes',
        INTERVAL '32 minutes',
        TRUE,
        NOW(),
        NOW()
    );
    
    -- Session 3: Concert Tickets (Active, longer duration)
    INSERT INTO bidding_sessions (
        id, admin_id, product_id, upset_price, final_price, inventory,
        alpha, beta, gamma, start_time, end_time, duration, is_active,
        created_at, updated_at
    ) VALUES (
        uuid_generate_v4(),
        admin_user_id,
        concert_id,
        500.0,
        NULL,
        10,
        0.4,
        1200.0,
        2.5,
        NOW(),
        NOW() + INTERVAL '1 hour',
        INTERVAL '1 hour',
        TRUE,
        NOW(),
        NOW()
    );
    
    -- Session 4: Rolex (Not active yet - upcoming)
    INSERT INTO bidding_sessions (
        id, admin_id, product_id, upset_price, final_price, inventory,
        alpha, beta, gamma, start_time, end_time, duration, is_active,
        created_at, updated_at
    ) VALUES (
        uuid_generate_v4(),
        admin_user_id,
        rolex_id,
        5000.0,
        NULL,
        2,
        0.7,
        500.0,
        3.0,
        NOW() + INTERVAL '2 hours',
        NOW() + INTERVAL '4 hours',
        INTERVAL '2 hours',
        FALSE,  -- not active yet
        NOW(),
        NOW()
    );
    
    -- Session 5: PS5 (Active)
    INSERT INTO bidding_sessions (
        id, admin_id, product_id, upset_price, final_price, inventory,
        alpha, beta, gamma, start_time, end_time, duration, is_active,
        created_at, updated_at
    ) VALUES (
        uuid_generate_v4(),
        admin_user_id,
        ps5_id,
        800.0,
        NULL,
        8,
        0.5,
        1000.0,
        2.0,
        NOW() - INTERVAL '1 minute',
        NOW() + INTERVAL '45 minutes',
        INTERVAL '46 minutes',
        TRUE,
        NOW(),
        NOW()
    );
END $$;

-- ============================================
-- INSERT SAMPLE BIDS (for testing leaderboard)
-- ============================================

DO $$
DECLARE
    session_id UUID;
    user1_id UUID;
    user2_id UUID;
    user3_id UUID;
    user4_id UUID;
    user5_id UUID;
BEGIN
    -- Get first active session (Sneakers)
    SELECT id INTO session_id FROM bidding_sessions WHERE is_active = TRUE LIMIT 1;
    
    -- Get user IDs
    SELECT id INTO user1_id FROM users WHERE username = 'user1';
    SELECT id INTO user2_id FROM users WHERE username = 'user2';
    SELECT id INTO user3_id FROM users WHERE username = 'user3';
    SELECT id INTO user4_id FROM users WHERE username = 'user4';
    SELECT id INTO user5_id FROM users WHERE username = 'user5';
    
    -- Insert sample bids
    INSERT INTO bidding_session_bids (id, session_id, user_id, bid_price, bid_score, created_at, updated_at) VALUES
    (uuid_generate_v4(), session_id, user1_id, 250.0, 1125.0, NOW() - INTERVAL '4 minutes', NOW()),
    (uuid_generate_v4(), session_id, user2_id, 300.0, 1153.0, NOW() - INTERVAL '3 minutes', NOW()),
    (uuid_generate_v4(), session_id, user3_id, 280.0, 1144.0, NOW() - INTERVAL '2 minutes', NOW()),
    (uuid_generate_v4(), session_id, user4_id, 220.0, 1111.6, NOW() - INTERVAL '1 minute', NOW()),
    (uuid_generate_v4(), session_id, user5_id, 350.0, 1177.4, NOW() - INTERVAL '30 seconds', NOW());
END $$;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check users
SELECT 'Users Created:' as info, COUNT(*) as count FROM users;
SELECT username, email, is_admin, weight FROM users ORDER BY is_admin DESC, username;

-- Check products
SELECT 'Products Created:' as info, COUNT(*) as count FROM bidding_products;
SELECT name, description FROM bidding_products;

-- Check sessions
SELECT 'Sessions Created:' as info, COUNT(*) as count FROM bidding_sessions;
SELECT 
    bp.name as product_name,
    bs.upset_price,
    bs.inventory,
    bs.is_active,
    bs.start_time,
    bs.end_time
FROM bidding_sessions bs
JOIN bidding_products bp ON bs.product_id = bp.id
ORDER BY bs.start_time;

-- Check bids
SELECT 'Bids Created:' as info, COUNT(*) as count FROM bidding_session_bids;
SELECT 
    u.username,
    bsb.bid_price,
    bsb.bid_score
FROM bidding_session_bids bsb
JOIN users u ON bsb.user_id = u.id
ORDER BY bsb.bid_score DESC;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '✓ Test data inserted successfully!';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - 11 users (1 admin, 10 regular)';
    RAISE NOTICE '  - 5 products';
    RAISE NOTICE '  - 5 bidding sessions (4 active, 1 upcoming)';
    RAISE NOTICE '  - 5 sample bids';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Test credentials:';
    RAISE NOTICE '  admin / admin123';
    RAISE NOTICE '  user1 / test123';
    RAISE NOTICE '  user2 / test123';
    RAISE NOTICE '  ... (user3-user10 / test123)';
    RAISE NOTICE '============================================';
END $$;