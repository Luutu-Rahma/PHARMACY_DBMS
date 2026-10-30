-- Run only when inspection confirms these triggers are absent.
-- Do not run this file if either trigger already exists; preserve the existing definition.
-- These triggers provide the exact existing desktop behavior: validate, price, deduct stock once, total the sale.
DELIMITER $$ CREATE TRIGGER trg_sale_before_insert BEFORE
INSERT ON SALES_ITEMS FOR EACH ROW BEGIN
DECLARE v_left INT;
DECLARE v_exp DATE;
DECLARE v_price DECIMAL(12, 2);
SELECT QuantityLeft,
    ExpiryDate,
    UnitPrice INTO v_left,
    v_exp,
    v_price
FROM INVENTORY_BATCHES
WHERE BatchID = NEW.BatchID;
IF v_exp <= CURDATE() THEN SIGNAL SQLSTATE '45000'
SET MESSAGE_TEXT = 'Sale blocked: batch is expired';
ELSEIF v_left < NEW.QuantitySold THEN SIGNAL SQLSTATE '45000'
SET MESSAGE_TEXT = 'Sale blocked: insufficient stock in batch';
END IF;
SET NEW.SubTotal = NEW.QuantitySold * v_price;
END $$ CREATE TRIGGER trg_sale_after_insert
AFTER
INSERT ON SALES_ITEMS FOR EACH ROW BEGIN
UPDATE INVENTORY_BATCHES
SET QuantityLeft = QuantityLeft - NEW.QuantitySold
WHERE BatchID = NEW.BatchID;
UPDATE TRANSACTIONS
SET TotalAmount = TotalAmount + NEW.SubTotal
WHERE TransactionID = NEW.TransactionID;
END $$ DELIMITER;