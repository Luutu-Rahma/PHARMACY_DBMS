-- Optional least-privilege application role grants for PostgreSQL/Supabase.
-- Execute as the project/database owner after schema and trigger setup.
-- This defines a group role only: create a LOGIN role through your trusted
-- database administration method, then GRANT pharmaflow_app TO that login.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pharmaflow_app') THEN
        CREATE ROLE pharmaflow_app NOLOGIN;
    END IF;
END $$;

DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO pharmaflow_app', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO pharmaflow_app;
GRANT SELECT ON users, categories, suppliers, drugs, inventory_batches, transactions, sales_items TO pharmaflow_app;
GRANT INSERT, UPDATE ON users, categories, suppliers, drugs TO pharmaflow_app;
GRANT INSERT ON inventory_batches, transactions, sales_items TO pharmaflow_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pharmaflow_app;
GRANT EXECUTE ON FUNCTION sp_fifo_batches(integer) TO pharmaflow_app;

-- Trigger functions are SECURITY DEFINER and are owned by the role that ran
-- 02_functions_triggers.sql. Do not grant the runtime role direct table UPDATE
-- on inventory_batches or transactions; triggers apply those changes.
REVOKE ALL ON FUNCTION pharmacy_prepare_sale_item() FROM PUBLIC;
REVOKE ALL ON FUNCTION pharmacy_apply_sale_item() FROM PUBLIC;
