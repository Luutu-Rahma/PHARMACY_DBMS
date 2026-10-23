-- =============================================================
-- 03b_seed_extra.sql - extra sample data
-- Run AFTER 03_seed.sql (needs the existing IDs):
--   categories 1-3, suppliers 1-2, drugs 1-3, batches 1-5,
--   transactions 1-2, users 1-4
-- Sales go through the triggers, so stock and totals update themselves.
-- =============================================================
USE pharmacy_sales_and_inventory_db;

-- Categories 4-6
INSERT INTO CATEGORIES (CategoryName, Description) VALUES
('Vitamins & Supplements', 'Nutritional supplements and vitamins'),
('Antacids & Digestive',   'Treat acidity and digestive complaints'),
('Antihistamines',         'Treat allergies');

-- Suppliers 3-5
INSERT INTO SUPPLIERS (SupplierName, ContactPerson, PhoneNumber, Email, Address) VALUES
('PharmaPlus East Africa',  'Grace Akello',  '+256772111222', 'orders@pharmaplus.ug', 'Ntinda, Kampala'),
('Kampala Medical Stores',  'David Mugisha', '+256701333444', 'info@kms.co.ug',       'Nakawa, Kampala'),
('Nile Health Distributors','Sarah Nankya',  '+256782555666', 'sales@nilehealth.ug',  'Jinja Road, Kampala');

-- Drugs 4-15
INSERT INTO DRUGS (CategoryID, GenericName, BrandName, UnitMeasure, UnitPrice) VALUES
(1, 'Ibuprofen',            'Brufen',     'tablets',  700.00),  -- 4
(1, 'Diclofenac',           'Voltaren',   'tablets',  900.00),  -- 5
(2, 'Ciprofloxacin',        'Ciprobay',   'tablets', 1500.00),  -- 6
(2, 'Azithromycin',         'Zithromax',  'tablets', 3500.00),  -- 7
(2, 'Metronidazole',        'Flagyl',     'tablets',  400.00),  -- 8
(3, 'Quinine',              'Quinine Sulphate', 'tablets', 1000.00), -- 9
(4, 'Vitamin C',            'Celin',      'tablets',  300.00),  -- 10
(4, 'Multivitamin',         'Multivit',   'tablets', 1500.00),  -- 11
(5, 'Omeprazole',           'Losec',      'capsules',1200.00),  -- 12
(5, 'Aluminium Hydroxide',  'Maalox',     'tablets',  900.00),  -- 13
(6, 'Cetirizine',           'Zyrtec',     'tablets',  600.00),  -- 14
(6, 'Loratadine',           'Claritin',   'tablets',  700.00);  -- 15

-- Batches 6-23 (20 and 21 are expired, 18 and 19 expire soon)
INSERT INTO INVENTORY_BATCHES
 (DrugID, SupplierID, BatchNumber, QuantityReceived, QuantityLeft, MFD, ExpiryDate, UnitPrice) VALUES
(4,  3, 'IBU-26-001', 200, 200, CURDATE() - INTERVAL 4 MONTH,  CURDATE() + INTERVAL 20 MONTH,  700.00), -- 6
(5,  3, 'DIC-26-001', 150, 150, CURDATE() - INTERVAL 3 MONTH,  CURDATE() + INTERVAL 18 MONTH,  900.00), -- 7
(6,  4, 'CIP-26-001', 120, 120, CURDATE() - INTERVAL 2 MONTH,  CURDATE() + INTERVAL 24 MONTH, 1500.00), -- 8
(7,  4, 'AZI-26-001',  60,  60, CURDATE() - INTERVAL 2 MONTH,  CURDATE() + INTERVAL 22 MONTH, 3500.00), -- 9
(8,  3, 'MET-26-001', 300, 300, CURDATE() - INTERVAL 5 MONTH,  CURDATE() + INTERVAL 16 MONTH,  400.00), -- 10
(9,  5, 'QUI-26-001', 100, 100, CURDATE() - INTERVAL 3 MONTH,  CURDATE() + INTERVAL 14 MONTH, 1000.00), -- 11
(10, 5, 'VTC-26-001', 250, 250, CURDATE() - INTERVAL 2 MONTH,  CURDATE() + INTERVAL 12 MONTH,  300.00), -- 12
(11, 5, 'MUL-26-001',  90,  90, CURDATE() - INTERVAL 1 MONTH,  CURDATE() + INTERVAL 24 MONTH, 1500.00), -- 13
(12, 4, 'OME-26-001', 110, 110, CURDATE() - INTERVAL 2 MONTH,  CURDATE() + INTERVAL 20 MONTH, 1200.00), -- 14
(13, 3, 'ALH-26-001', 140, 140, CURDATE() - INTERVAL 3 MONTH,  CURDATE() + INTERVAL 15 MONTH,  900.00), -- 15
(14, 4, 'CET-26-001', 200, 200, CURDATE() - INTERVAL 2 MONTH,  CURDATE() + INTERVAL 26 MONTH,  600.00), -- 16
(15, 4, 'LOR-26-001', 180, 180, CURDATE() - INTERVAL 1 MONTH,  CURDATE() + INTERVAL 28 MONTH,  700.00), -- 17
(2,  3, 'AMX-26-002', 100, 100, CURDATE() - INTERVAL 1 MONTH,  CURDATE() + INTERVAL 2 MONTH,  1200.00), -- 18 expiring soon
(3,  4, 'COA-26-002',  60,  60, CURDATE() - INTERVAL 10 MONTH, CURDATE() + INTERVAL 1 MONTH,  8000.00), -- 19 expiring soon
(4,  3, 'IBU-OLD-001', 50,  50, CURDATE() - INTERVAL 26 MONTH, CURDATE() - INTERVAL 20 DAY,    650.00), -- 20 EXPIRED
(8,  4, 'MET-OLD-001', 80,  80, CURDATE() - INTERVAL 30 MONTH, CURDATE() - INTERVAL 1 MONTH,   380.00), -- 21 EXPIRED
(1,  2, 'PCM-26-004', 400, 400, CURDATE() - INTERVAL 1 MONTH,  CURDATE() + INTERVAL 30 MONTH,  500.00), -- 22
(10, 3, 'VTC-26-002', 150, 150, CURDATE() - INTERVAL 1 MONTH,  CURDATE() + INTERVAL 18 MONTH,  300.00); -- 23

-- Transactions 3-20 (all by the cashier, UserID 4)
INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES
(4, 'Cash'), (4, 'Mobile Money'), (4, 'Cash'), (4, 'Cash'), (4, 'Mobile Money'),
(4, 'Cash'), (4, 'Cash'), (4, 'Mobile Money'), (4, 'Cash'), (4, 'Cash'),
(4, 'Mobile Money'), (4, 'Cash'), (4, 'Cash'), (4, 'Mobile Money'), (4, 'Cash'),
(4, 'Cash'), (4, 'Mobile Money'), (4, 'Cash');

-- Sale items: only non-expired batches, quantities within stock
INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold) VALUES
(3, 3, 30), (3, 6, 10),
(4, 8, 14), (4, 10, 20),
(5, 12, 25),
(6, 16, 10), (6, 17, 10),
(7, 9, 5),  (7, 14, 7),
(8, 2, 40),
(9, 4, 15),
(10, 7, 12), (10, 15, 6),
(11, 11, 10), (11, 13, 4),
(12, 22, 50),
(13, 5, 3), (13, 19, 4),
(14, 18, 10),
(15, 23, 30), (15, 12, 15),
(16, 6, 20), (16, 7, 8),
(17, 3, 45),
(18, 8, 6), (18, 14, 3),
(19, 4, 10), (19, 18, 5), (19, 16, 8),
(20, 22, 25), (20, 10, 10);

-- Spread the sales over the last 18 days (useful for charts)
UPDATE TRANSACTIONS
   SET `TimeStamp` = NOW() - INTERVAL (21 - TransactionID) DAY
 WHERE TransactionID > 2;
