USE pharmacy_sales_and_inventory_db;

INSERT INTO USERS(FullName, UserName, Password, `Role`) VALUES
('Luutu Rahma', 'rahma123', 'secure_hash_123', 'Admin'),
('Nambuya Raudha', 'rau123', 'secure_hash_456','Cashier');

INSERT INTO SUPPLIERS (SupplierName, ContactPerson, PhoneNumber, Email, Address)VALUES
('Global Pharma Ltd','Luutu Leilah', '+256777706392', 'lei@gmail.com', 'Kampala Road');

INSERT INTO CATEGORIES(CategoryName, Description) VALUES
('Painkillers', 'General pain relief meds'),
('Antibiotics', 'Used to treat bacterial infectons');

INSERT INTO DRUGS(CategoryID, GenericName, BrandName, UnitMeasure, UnitPrice)VALUES
(1, 'Paracetamol', 'Panadol Extra', 500.0, 5000.0),
(2, 'Amoxillin', 'Amoxil Capsules', 250.0, 12000.0);

INSERT INTO INVENTORY_BATCHES (DrugID, SupplierID, BatchNumber, QuantityRecieved, QuantityLeft,MFD, ExpiryDate, UnitPrice)VALUES
(1, 1, 'B-26-001', 100, 100, '2026-01-10', '2028-10-10', 4500.0);

INSERT INTO TRANSACTIONS (UserID, TotalAmount, PaymentMethod)VALUES
(2, 17000.0, 'MOBILE MONEY');

INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold, SubTotal)VALUES
(1, 1, 1, 5000.0);