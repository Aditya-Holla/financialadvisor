-- Setup Test Users for Supabase Authentication
-- Run this in your Supabase SQL Editor after creating users via the Auth UI

-- Note: Users must be created via Supabase Auth UI or API first
-- This script only creates/updates the profiles table entries

-- 1. Create approved user profile (user should be created via Auth UI with email: test@approved.com)
-- Replace 'USER_ID_FROM_AUTH' with the actual user ID from auth.users table
INSERT INTO profiles (
    user_id,
    monthly_income,
    monthly_expenses,
    emergency_fund_balance,
    credit_card_apr,
    goals,
    created_at,
    updated_at
) VALUES (
    (SELECT id FROM auth.users WHERE email = 'test@approved.com' LIMIT 1),
    8000.00,  -- $8,000 monthly income
    4000.00,  -- $4,000 monthly expenses
    15000.00, -- $15,000 emergency fund (3.75 months)
    0.0,      -- No credit card debt
    '[
        {
            "name": "Retirement",
            "target_amount": 1000000,
            "target_date": "2045-01-01",
            "priority": "high"
        }
    ]'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (user_id) DO UPDATE SET
    monthly_income = EXCLUDED.monthly_income,
    monthly_expenses = EXCLUDED.monthly_expenses,
    emergency_fund_balance = EXCLUDED.emergency_fund_balance,
    credit_card_apr = EXCLUDED.credit_card_apr,
    goals = EXCLUDED.goals,
    updated_at = NOW();

-- 2. Create blocked user profile (user should be created via Auth UI with email: test@blocked.com)
INSERT INTO profiles (
    user_id,
    monthly_income,
    monthly_expenses,
    emergency_fund_balance,
    credit_card_apr,
    goals,
    created_at,
    updated_at
) VALUES (
    (SELECT id FROM auth.users WHERE email = 'test@blocked.com' LIMIT 1),
    3000.00,  -- $3,000 monthly income
    3500.00,  -- $3,500 monthly expenses (negative cash flow!)
    2000.00,  -- $2,000 emergency fund (0.57 months - below 3 month minimum)
    0.25,     -- 25% APR credit card debt
    '[
        {
            "name": "Emergency Fund",
            "target_amount": 10000,
            "target_date": "2024-06-01",
            "priority": "high"
        }
    ]'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (user_id) DO UPDATE SET
    monthly_income = EXCLUDED.monthly_income,
    monthly_expenses = EXCLUDED.monthly_expenses,
    emergency_fund_balance = EXCLUDED.emergency_fund_balance,
    credit_card_apr = EXCLUDED.credit_card_apr,
    goals = EXCLUDED.goals,
    updated_at = NOW();

-- 3. Create snapshot for approved user
INSERT INTO snapshots (
    user_id,
    cash_balance,
    positions,
    created_at
) VALUES (
    (SELECT id FROM auth.users WHERE email = 'test@approved.com' LIMIT 1),
    50000.00,  -- $50,000 cash
    '[]'::jsonb,  -- No positions yet
    NOW()
)
ON CONFLICT DO NOTHING;

-- 4. Create snapshot for blocked user
INSERT INTO snapshots (
    user_id,
    cash_balance,
    positions,
    created_at
) VALUES (
    (SELECT id FROM auth.users WHERE email = 'test@blocked.com' LIMIT 1),
    2000.00,  -- $2,000 cash (low emergency fund)
    '[]'::jsonb,  -- No positions yet
    NOW()
)
ON CONFLICT DO NOTHING;

-- Instructions:
-- 1. First, create users in Supabase Auth UI:
--    - Go to Authentication > Users in Supabase dashboard
--    - Click "Add user" > "Create new user"
--    - Create user with email: test@approved.com, password: test123456
--    - Create user with email: test@blocked.com, password: test123456
--
-- 2. Then run this SQL script in Supabase SQL Editor
--
-- 3. Verify users exist:
--    SELECT u.email, p.* 
--    FROM auth.users u 
--    LEFT JOIN profiles p ON u.id = p.user_id 
--    WHERE u.email IN ('test@approved.com', 'test@blocked.com');

