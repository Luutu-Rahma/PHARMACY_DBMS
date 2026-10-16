-- ============================================================
-- 06_tests.sql  -  each statement below SHOULD FAIL (that is the point)
-- Run them one at a time and screenshot the errors for your report.
-- ============================================================
USE pharmacy_sales_and_inventory_db;

-- T1: sell from the EXPIRED batch (BatchID 1)            -> 'batch is expired'
INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES (4,'Cash');
INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold) VALUES (LAST_INSERT_ID(), 1, 1);

-- T2: sell more than is in stock                          -> 'insufficient stock'
INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES (4,'Cash');
INSERT INTO SALES_ITEMS (TransactionID, BatchID, QuantitySold) VALUES (LAST_INSERT_ID(), 4, 99999);

-- T3: invalid role                                        -> CHECK constraint fails
INSERT INTO USERS (FullName, UserName, Password, `Role`) VALUES ('Test','t1','x','Janitor');

-- T4: invalid payment method                              -> CHECK constraint fails
INSERT INTO TRANSACTIONS (UserID, PaymentMethod) VALUES (4,'Card');

-- T5: duplicate username                                  -> UNIQUE violation
INSERT INTO USERS (FullName, UserName, Password, `Role`) VALUES ('Dup','rahma','x','Cashier');

-- T6: expiry before manufacture date                      -> CHECK constraint fails
INSERT INTO INVENTORY_BATCHES (DrugID,SupplierID,BatchNumber,QuantityReceived,QuantityLeft,MFD,ExpiryDate,UnitPrice)
VALUES (1,1,'BAD-001',10,10,'2026-06-01','2026-01-01',100);
