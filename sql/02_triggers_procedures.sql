-- ============================================================
-- 02_triggers_procedures.sql
-- Business logic: stock validation, auto-deduction, auto totals,
-- and a FIFO helper procedure.
-- NOTE: uses DELIMITER -> run with setup.bat / mysql CLI / phpMyAdmin.
-- ============================================================
USE pharmacy_sales_and_inventory_db;

DROP TRIGGER IF EXISTS trg_sale_before_insert;
DROP TRIGGER IF EXISTS trg_sale_after_insert;
DROP PROCEDURE IF EXISTS sp_fifo_batches;

DELIMITER $$

-- Before a line item is saved: block expired / insufficient stock,
-- and calculate SubTotal = QuantitySold * batch UnitPrice
CREATE TRIGGER trg_sale_before_insert
BEFORE INSERT ON SALES_ITEMS
FOR EACH ROW
BEGIN
    DECLARE v_left  INT;
    DECLARE v_exp   DATE;
    DECLARE v_price DECIMAL(12,2);

    SELECT QuantityLeft, ExpiryDate, UnitPrice
      INTO v_left, v_exp, v_price
      FROM INVENTORY_BATCHES
     WHERE BatchID = NEW.BatchID;

    IF v_exp <= CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Sale blocked: batch is expired';
    ELSEIF v_left < NEW.QuantitySold THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Sale blocked: insufficient stock in batch';
    END IF;

    SET NEW.SubTotal = NEW.QuantitySold * v_price;
END$$

-- After a line item is saved: deduct stock and update the receipt total
CREATE TRIGGER trg_sale_after_insert
AFTER INSERT ON SALES_ITEMS
FOR EACH ROW
BEGIN
    UPDATE INVENTORY_BATCHES
       SET QuantityLeft = QuantityLeft - NEW.QuantitySold
     WHERE BatchID = NEW.BatchID;

    UPDATE TRANSACTIONS
       SET TotalAmount = TotalAmount + NEW.SubTotal
     WHERE TransactionID = NEW.TransactionID;
END$$

-- FIFO helper: list sellable batches for a drug, soonest expiry first
CREATE PROCEDURE sp_fifo_batches(IN p_drug_id INT)
BEGIN
    SELECT BatchID, BatchNumber, QuantityLeft, ExpiryDate, UnitPrice
      FROM INVENTORY_BATCHES
     WHERE DrugID = p_drug_id
       AND QuantityLeft > 0
       AND ExpiryDate > CURDATE()
     ORDER BY ExpiryDate ASC;
END$$

DELIMITER ;
