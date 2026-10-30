-- Run only when inspection confirms sp_fifo_batches is absent.
-- This matches the FIFO helper in the existing SQL scripts.
DELIMITER $$ CREATE PROCEDURE sp_fifo_batches(IN p_drug_id INT) BEGIN
SELECT BatchID,
    BatchNumber,
    QuantityLeft,
    ExpiryDate,
    UnitPrice
FROM INVENTORY_BATCHES
WHERE DrugID = p_drug_id
    AND QuantityLeft > 0
    AND ExpiryDate > CURDATE()
ORDER BY ExpiryDate ASC;
END $$ DELIMITER;