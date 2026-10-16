-- ============================================================
-- 05_roles_privileges.sql  -  database-level role-based access
-- Triggers run with the privileges of their DEFINER (root), so
-- cashiers do NOT need UPDATE rights on stock for auto-deduction.
-- Change the demo passwords before any real use.
-- ============================================================
USE pharmacy_sales_and_inventory_db;

CREATE USER IF NOT EXISTS 'pf_admin'@'localhost'      IDENTIFIED BY 'Admin@123';
CREATE USER IF NOT EXISTS 'pf_inventory'@'localhost'  IDENTIFIED BY 'Inventory@123';
CREATE USER IF NOT EXISTS 'pf_pharmacist'@'localhost' IDENTIFIED BY 'Pharmacist@123';
CREATE USER IF NOT EXISTS 'pf_cashier'@'localhost'    IDENTIFIED BY 'Cashier@123';

-- Pharmacy Manager (Admin): full control + reports
GRANT ALL PRIVILEGES ON pharmacy_sales_and_inventory_db.* TO 'pf_admin'@'localhost';

-- Inventory Manager: deliveries, batches, suppliers, drug catalogue
GRANT SELECT, INSERT, UPDATE ON pharmacy_sales_and_inventory_db.INVENTORY_BATCHES TO 'pf_inventory'@'localhost';
GRANT SELECT, INSERT, UPDATE ON pharmacy_sales_and_inventory_db.SUPPLIERS         TO 'pf_inventory'@'localhost';
GRANT SELECT, INSERT, UPDATE ON pharmacy_sales_and_inventory_db.DRUGS             TO 'pf_inventory'@'localhost';
GRANT SELECT, INSERT, UPDATE ON pharmacy_sales_and_inventory_db.CATEGORIES        TO 'pf_inventory'@'localhost';

-- Pharmacist: read catalogue, stock and sales (dispensing oversight)
GRANT SELECT ON pharmacy_sales_and_inventory_db.DRUGS             TO 'pf_pharmacist'@'localhost';
GRANT SELECT ON pharmacy_sales_and_inventory_db.CATEGORIES        TO 'pf_pharmacist'@'localhost';
GRANT SELECT ON pharmacy_sales_and_inventory_db.INVENTORY_BATCHES TO 'pf_pharmacist'@'localhost';
GRANT SELECT ON pharmacy_sales_and_inventory_db.TRANSACTIONS      TO 'pf_pharmacist'@'localhost';
GRANT SELECT ON pharmacy_sales_and_inventory_db.SALES_ITEMS       TO 'pf_pharmacist'@'localhost';
GRANT EXECUTE ON PROCEDURE pharmacy_sales_and_inventory_db.sp_fifo_batches TO 'pf_pharmacist'@'localhost';

-- Cashier: ring up sales only
GRANT SELECT ON pharmacy_sales_and_inventory_db.DRUGS             TO 'pf_cashier'@'localhost';
GRANT SELECT ON pharmacy_sales_and_inventory_db.INVENTORY_BATCHES TO 'pf_cashier'@'localhost';
GRANT SELECT, INSERT ON pharmacy_sales_and_inventory_db.TRANSACTIONS TO 'pf_cashier'@'localhost';
GRANT SELECT, INSERT ON pharmacy_sales_and_inventory_db.SALES_ITEMS  TO 'pf_cashier'@'localhost';
GRANT EXECUTE ON PROCEDURE pharmacy_sales_and_inventory_db.sp_fifo_batches TO 'pf_cashier'@'localhost';

FLUSH PRIVILEGES;
