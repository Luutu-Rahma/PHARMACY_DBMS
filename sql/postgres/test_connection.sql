-- Run explicitly in Supabase SQL editor or with psql to verify network/schema access.
-- It performs read-only checks and does not create, seed, or modify data.
SELECT current_database() AS database_name,
       current_user AS connected_role,
       version() AS postgres_version;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('users', 'categories', 'suppliers', 'drugs', 'inventory_batches', 'transactions', 'sales_items')
ORDER BY table_name;
