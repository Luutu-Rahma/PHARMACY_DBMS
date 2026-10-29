-- Development/demo seed adapted from sql/03_seed.sql and sql/03b_seed_extra.sql.
-- Run once against a fresh schema after 01_schema.sql and 02_functions_triggers.sql.
-- This script refuses to run when users already exist and never deletes data.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM users LIMIT 1) THEN
        RAISE EXCEPTION 'Seed stopped: users already exist. Use a fresh, empty development database.';
    END IF;
END $$;

INSERT INTO users (userid, fullname, username, password, role) VALUES
(1, 'Luutu Rahma Namayanja', 'rahma', '663b067861154c725a2d3720ba7e5af643e65919aecfe481dd450394f53ff9a2', 'Admin'),
(2, 'Ojambo Nicholas', 'nicholas', '63310ce9a788cd1a98735f54148470f99065482d6e37d0bf7d02b9b57ca83560', 'InventoryManager'),
(3, 'Mumbere Breiline', 'breiline', '2af330aa097ce7aa4e465f63c695903fba92a098129aa3b5bf6997f772b8c2e5', 'Pharmacist'),
(4, 'Nambuya Raudha', 'raudha', '6f1e8dfdf2716f0e312da555e16f0488dc6c5bcfd7c6150808fc08fc579f61e6', 'Cashier'),
(5, 'Luutu Gregory', 'luutu', '4e88e5b9d4883babcb01181f3dd7afcb615937b0f1a46291ffcaa1f406d54ca5', 'Pharmacist');

INSERT INTO categories (categoryid, categoryname, description) VALUES
(1, 'Painkillers', 'General pain relief medication'),
(2, 'Antibiotics', 'Used to treat bacterial infections'),
(3, 'Antimalarials', 'Used to treat and prevent malaria'),
(4, 'Vitamins & Supplements', 'Nutritional supplements and vitamins'),
(5, 'Antacids & Digestive', 'Treat acidity and digestive complaints'),
(6, 'Antihistamines', 'Treat allergies');

INSERT INTO suppliers (supplierid, suppliername, contactperson, phonenumber, email, address) VALUES
(1, 'Global Pharma Ltd', 'Luutu Leilah', '+256777706392', 'lei@gmail.com', 'Kampala Road, Kampala'),
(2, 'MediSupply Uganda', 'John Okello', '+256700123456', 'sales@medisupply.ug', 'Industrial Area, Kampala'),
(3, 'PharmaPlus East Africa', 'Grace Akello', '+256772111222', 'orders@pharmaplus.ug', 'Ntinda, Kampala'),
(4, 'Kampala Medical Stores', 'David Mugisha', '+256701333444', 'info@kms.co.ug', 'Nakawa, Kampala'),
(5, 'Nile Health Distributors', 'Sarah Nankya', '+256782555666', 'sales@nilehealth.ug', 'Jinja Road, Kampala');

INSERT INTO drugs (drugid, categoryid, genericname, brandname, unitmeasure, unitprice) VALUES
(1, 1, 'Paracetamol', 'Panadol Extra', 'tablets', 500.00),
(2, 2, 'Amoxicillin', 'Amoxil Capsules', 'capsules', 1200.00),
(3, 3, 'Artemether/Lumefantrine', 'Coartem', 'tablets', 8000.00),
(4, 1, 'Ibuprofen', 'Brufen', 'tablets', 700.00),
(5, 1, 'Diclofenac', 'Voltaren', 'tablets', 900.00),
(6, 2, 'Ciprofloxacin', 'Ciprobay', 'tablets', 1500.00),
(7, 2, 'Azithromycin', 'Zithromax', 'tablets', 3500.00),
(8, 2, 'Metronidazole', 'Flagyl', 'tablets', 400.00),
(9, 3, 'Quinine', 'Quinine Sulphate', 'tablets', 1000.00),
(10, 4, 'Vitamin C', 'Celin', 'tablets', 300.00),
(11, 4, 'Multivitamin', 'Multivit', 'tablets', 1500.00),
(12, 5, 'Omeprazole', 'Losec', 'capsules', 1200.00),
(13, 5, 'Aluminium Hydroxide', 'Maalox', 'tablets', 900.00),
(14, 6, 'Cetirizine', 'Zyrtec', 'tablets', 600.00),
(15, 6, 'Loratadine', 'Claritin', 'tablets', 700.00);

INSERT INTO inventory_batches
(batchid, drugid, supplierid, batchnumber, quantityreceived, quantityleft, mfd, expirydate, unitprice) VALUES
(1, 1, 1, 'PCM-OLD-001', 100, 100, CURRENT_DATE - INTERVAL '30 months', CURRENT_DATE - INTERVAL '10 days', 450.00),
(2, 1, 1, 'PCM-26-002', 200, 200, CURRENT_DATE - INTERVAL '12 months', CURRENT_DATE + INTERVAL '2 months', 500.00),
(3, 1, 2, 'PCM-26-003', 300, 300, CURRENT_DATE - INTERVAL '2 months', CURRENT_DATE + INTERVAL '24 months', 500.00),
(4, 2, 2, 'AMX-26-001', 150, 150, CURRENT_DATE - INTERVAL '3 months', CURRENT_DATE + INTERVAL '18 months', 1200.00),
(5, 3, 1, 'COA-26-001', 80, 80, CURRENT_DATE - INTERVAL '1 month', CURRENT_DATE + INTERVAL '20 months', 8000.00),
(6, 4, 3, 'IBU-26-001', 200, 200, CURRENT_DATE - INTERVAL '4 months', CURRENT_DATE + INTERVAL '20 months', 700.00),
(7, 5, 3, 'DIC-26-001', 150, 150, CURRENT_DATE - INTERVAL '3 months', CURRENT_DATE + INTERVAL '18 months', 900.00),
(8, 6, 4, 'CIP-26-001', 120, 120, CURRENT_DATE - INTERVAL '2 months', CURRENT_DATE + INTERVAL '24 months', 1500.00),
(9, 7, 4, 'AZI-26-001', 60, 60, CURRENT_DATE - INTERVAL '2 months', CURRENT_DATE + INTERVAL '22 months', 3500.00),
(10, 8, 3, 'MET-26-001', 300, 300, CURRENT_DATE - INTERVAL '5 months', CURRENT_DATE + INTERVAL '16 months', 400.00),
(11, 9, 5, 'QUI-26-001', 100, 100, CURRENT_DATE - INTERVAL '3 months', CURRENT_DATE + INTERVAL '14 months', 1000.00),
(12, 10, 5, 'VTC-26-001', 250, 250, CURRENT_DATE - INTERVAL '2 months', CURRENT_DATE + INTERVAL '12 months', 300.00),
(13, 11, 5, 'MUL-26-001', 90, 90, CURRENT_DATE - INTERVAL '1 month', CURRENT_DATE + INTERVAL '24 months', 1500.00),
(14, 12, 4, 'OME-26-001', 110, 110, CURRENT_DATE - INTERVAL '2 months', CURRENT_DATE + INTERVAL '20 months', 1200.00),
(15, 13, 3, 'ALH-26-001', 140, 140, CURRENT_DATE - INTERVAL '3 months', CURRENT_DATE + INTERVAL '15 months', 900.00),
(16, 14, 4, 'CET-26-001', 200, 200, CURRENT_DATE - INTERVAL '2 months', CURRENT_DATE + INTERVAL '26 months', 600.00),
(17, 15, 4, 'LOR-26-001', 180, 180, CURRENT_DATE - INTERVAL '1 month', CURRENT_DATE + INTERVAL '28 months', 700.00),
(18, 2, 3, 'AMX-26-002', 100, 100, CURRENT_DATE - INTERVAL '1 month', CURRENT_DATE + INTERVAL '2 months', 1200.00),
(19, 3, 4, 'COA-26-002', 60, 60, CURRENT_DATE - INTERVAL '10 months', CURRENT_DATE + INTERVAL '1 month', 8000.00),
(20, 4, 3, 'IBU-OLD-001', 50, 50, CURRENT_DATE - INTERVAL '26 months', CURRENT_DATE - INTERVAL '20 days', 650.00),
(21, 8, 4, 'MET-OLD-001', 80, 80, CURRENT_DATE - INTERVAL '30 months', CURRENT_DATE - INTERVAL '1 month', 380.00),
(22, 1, 2, 'PCM-26-004', 400, 400, CURRENT_DATE - INTERVAL '1 month', CURRENT_DATE + INTERVAL '30 months', 500.00),
(23, 10, 3, 'VTC-26-002', 150, 150, CURRENT_DATE - INTERVAL '1 month', CURRENT_DATE + INTERVAL '18 months', 300.00);

-- Twenty demo transactions, matching the original seed's payment mix and dates.
INSERT INTO transactions (transactionid, userid, timestamp, totalamount, paymentmethod) VALUES
(1, 4, CURRENT_TIMESTAMP, 0, 'Mobile Money'),
(2, 4, CURRENT_TIMESTAMP, 0, 'Cash'),
(3, 4, CURRENT_TIMESTAMP - INTERVAL '18 days', 0, 'Cash'),
(4, 4, CURRENT_TIMESTAMP - INTERVAL '17 days', 0, 'Mobile Money'),
(5, 4, CURRENT_TIMESTAMP - INTERVAL '16 days', 0, 'Cash'),
(6, 4, CURRENT_TIMESTAMP - INTERVAL '15 days', 0, 'Cash'),
(7, 4, CURRENT_TIMESTAMP - INTERVAL '14 days', 0, 'Mobile Money'),
(8, 4, CURRENT_TIMESTAMP - INTERVAL '13 days', 0, 'Cash'),
(9, 4, CURRENT_TIMESTAMP - INTERVAL '12 days', 0, 'Cash'),
(10, 4, CURRENT_TIMESTAMP - INTERVAL '11 days', 0, 'Mobile Money'),
(11, 4, CURRENT_TIMESTAMP - INTERVAL '10 days', 0, 'Cash'),
(12, 4, CURRENT_TIMESTAMP - INTERVAL '9 days', 0, 'Cash'),
(13, 4, CURRENT_TIMESTAMP - INTERVAL '8 days', 0, 'Mobile Money'),
(14, 4, CURRENT_TIMESTAMP - INTERVAL '7 days', 0, 'Cash'),
(15, 4, CURRENT_TIMESTAMP - INTERVAL '6 days', 0, 'Cash'),
(16, 4, CURRENT_TIMESTAMP - INTERVAL '5 days', 0, 'Mobile Money'),
(17, 4, CURRENT_TIMESTAMP - INTERVAL '4 days', 0, 'Cash'),
(18, 4, CURRENT_TIMESTAMP - INTERVAL '3 days', 0, 'Mobile Money'),
(19, 4, CURRENT_TIMESTAMP - INTERVAL '2 days', 0, 'Cash'),
(20, 4, CURRENT_TIMESTAMP - INTERVAL '1 day', 0, 'Cash');

-- Sale lines mirror the original demo transactions. Trigger functions calculate
-- subtotals and totals and deduct inventory as each line is inserted.
INSERT INTO sales_items (salesitemid, transactionid, batchid, quantitysold) VALUES
(1, 1, 2, 10), (2, 1, 5, 2), (3, 2, 4, 20),
(4, 3, 3, 30), (5, 3, 6, 10),
(6, 4, 8, 14), (7, 4, 10, 20),
(8, 5, 12, 25),
(9, 6, 16, 10), (10, 6, 17, 10),
(11, 7, 9, 5), (12, 7, 14, 7),
(13, 8, 2, 40),
(14, 9, 4, 15),
(15, 10, 7, 12), (16, 10, 15, 6),
(17, 11, 11, 10), (18, 11, 13, 4),
(19, 12, 22, 50),
(20, 13, 5, 3), (21, 13, 19, 4),
(22, 14, 18, 10),
(23, 15, 23, 30), (24, 15, 12, 15),
(25, 16, 6, 20), (26, 16, 7, 8),
(27, 17, 3, 45),
(28, 18, 8, 6), (29, 18, 14, 3),
(30, 19, 4, 10), (31, 19, 18, 5), (32, 19, 16, 8),
(33, 20, 22, 25), (34, 20, 10, 10);

SELECT setval(pg_get_serial_sequence('users', 'userid'), (SELECT MAX(userid) FROM users));
SELECT setval(pg_get_serial_sequence('categories', 'categoryid'), (SELECT MAX(categoryid) FROM categories));
SELECT setval(pg_get_serial_sequence('suppliers', 'supplierid'), (SELECT MAX(supplierid) FROM suppliers));
SELECT setval(pg_get_serial_sequence('drugs', 'drugid'), (SELECT MAX(drugid) FROM drugs));
SELECT setval(pg_get_serial_sequence('inventory_batches', 'batchid'), (SELECT MAX(batchid) FROM inventory_batches));
SELECT setval(pg_get_serial_sequence('transactions', 'transactionid'), (SELECT MAX(transactionid) FROM transactions));
SELECT setval(pg_get_serial_sequence('sales_items', 'salesitemid'), (SELECT MAX(salesitemid) FROM sales_items));
