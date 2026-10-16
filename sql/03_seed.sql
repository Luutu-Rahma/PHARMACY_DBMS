-- ============================================================
-- 03_seed.sql  -  sample data (run AFTER 01 and 02 so triggers
-- deduct stock and compute totals automatically)
-- Dates are relative to today so the demo always works.
-- ============================================================
USE pharmacy_sales_and_inventory_db;

-- One user per role. Passwords are SHA-256 hashes of 'Pass@123' (demo only).
INSERT INTO USERS (FullName, UserName, Password, `Role`) VALUES
('Luutu Rahma Namayanja', 'rahma',   SHA2('Pass@123',256), 'Admin'),
('Ojambo Nicholas',       'nicholas',SHA2('Pass@123',256), 'InventoryManager'),
('Mumbere Breiline',      'breiline',SHA2('Pass@123',256), 'Pharmacist'),
('Nambuya Raudha',        'raudha',  SHA2('Pass@123',256), 'Cashier');

INSERT INTO CATEGORIES (CategoryName, Description) VALUES
('Painkillers', 'General pain relief medication'),
('Antibiotics', 'Used to treat bacterial infections'),
('Antimalarials','Used to treat and prevent malaria');

INSERT INTO SUPPLIERS (SupplierName, ContactPerson, PhoneNumber, Email, Address) VALUES
('Global Pharma Ltd', 'Luutu Leilah', '+256777706392', 'lei@gmail.com', 'Kampala Road, Kampala'),
('MediSupply Uganda', 'John Okello',  '+256700123456', 'sales@medisupply.ug', 'Industrial Area, Kampala');

INSERT INTO DRUGS (CategoryID, GenericName, BrandName, UnitMeasure, UnitPrice) VALUES
(1, 'Paracetamol',  'Panadol Extra',   'tablets',  500.00),
(2, 'Amoxicillin',  'Amoxil Capsules', 'capsules', 1200.00),
(3, 'Artemether/Lumefantrine', 'Coartem', 'tablets', 8000.00);

-- Drug 1 has THREE batches: one expired, one expiring soon, one far away
INSERT INTO INVENTORY_BATCHES
 (DrugID, SupplierID, BatchNumber, QuantityReceived, QuantityLeft, MFD, ExpiryDate, UnitPrice) VALUES
(1, 1, 'PCM-OLD-001', 100, 100, CURDATE() - INTERVAL 30 MONTH, CURDATE() - INTERVAL 10 DAY,  450.00), -- EXPIRED
(1, 1, 'PCM-26-002',  200, 200, CURDATE() - INTERVAL 12 MONTH, CURDATE() + INTERVAL 2 MONTH, 500.00), -- expires soon (FIFO first)
(1, 2, 'PCM-26-003',  300, 300, CURDATE() - INTERVAL 2 MONTH,  CURDATE() + INTERVAL 24 MONTH,500.00),
(2, 2, 'AMX-26-001',  150, 150, CURDATE() - INTERVAL 3 MONTH,  CURDATE() + INTERVAL 18 MONTH,1200.00),
(3, 1, 'COA-26-001',   80,  80, CURDATE() - INTERVAL 1 MONTH,  CURDATE() + INTERVAL 20 MONTH,8000.00);

-- Sale 1 (Cashier, Mobile Money): 10 paracetamol from soonest-expiry batch + 2 coartem
INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES (4, 'Mobile Money');
INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold) VALUES
(1, 2, 10),
(1, 5, 2);

-- Sale 2 (Cashier, Cash): 20 amoxicillin
INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES (4, 'Cash');
INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold) VALUES
(2, 4, 20);
