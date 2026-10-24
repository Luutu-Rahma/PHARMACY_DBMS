-- ============================================================
-- 00_reset.sql  (DEV ONLY)
-- Drops the whole database AND the role accounts so you can rebuild
-- from scratch (05_roles_privileges.sql recreates the accounts).
-- WARNING: this deletes ALL data. Never run on real data.
-- ============================================================
DROP DATABASE IF EXISTS pharmacy_sales_and_inventory_db;

DROP USER IF EXISTS 'pf_login'@'localhost';
DROP USER IF EXISTS 'pf_admin'@'localhost';
DROP USER IF EXISTS 'pf_inventory'@'localhost';
DROP USER IF EXISTS 'pf_pharmacist'@'localhost';
DROP USER IF EXISTS 'pf_cashier'@'localhost';
