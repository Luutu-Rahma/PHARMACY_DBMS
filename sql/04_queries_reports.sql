-- ============================================================
-- 04_queries_reports.sql  -  one query per project objective
-- ============================================================
USE pharmacy_sales_and_inventory_db;

-- 1. FIFO: which batch to sell first for Drug 1 (Paracetamol)?
CALL sp_fifo_batches(1);

-- 2. Batches expiring within the next 90 days (still in stock)
SELECT d.GenericName, b.BatchNumber, b.QuantityLeft, b.ExpiryDate,
       DATEDIFF(b.ExpiryDate, CURDATE()) AS DaysToExpiry
  FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID = b.DrugID
 WHERE b.QuantityLeft > 0
   AND b.ExpiryDate BETWEEN CURDATE() AND CURDATE() + INTERVAL 90 DAY
 ORDER BY b.ExpiryDate;

-- 3. Expired stock still on the shelf (potential loss)
SELECT d.GenericName, b.BatchNumber, b.QuantityLeft, b.ExpiryDate,
       b.QuantityLeft * b.UnitPrice AS ValueAtRisk
  FROM INVENTORY_BATCHES b JOIN DRUGS d ON d.DrugID = b.DrugID
 WHERE b.ExpiryDate <= CURDATE() AND b.QuantityLeft > 0;

-- 4. Total sellable stock per drug (excludes expired)
SELECT d.DrugID, d.GenericName, c.CategoryName,
       COALESCE(SUM(CASE WHEN b.ExpiryDate > CURDATE() THEN b.QuantityLeft END),0) AS SellableStock
  FROM DRUGS d
  JOIN CATEGORIES c ON c.CategoryID = d.CategoryID
  LEFT JOIN INVENTORY_BATCHES b ON b.DrugID = d.DrugID
 GROUP BY d.DrugID, d.GenericName, c.CategoryName
 ORDER BY SellableStock;

-- 5. Staff accountability: sales handled per user
SELECT u.FullName, u.`Role`, COUNT(t.TransactionID) AS Transactions,
       COALESCE(SUM(t.TotalAmount),0) AS TotalSales
  FROM USERS u LEFT JOIN TRANSACTIONS t ON t.UserID = u.UserID
 GROUP BY u.UserID, u.FullName, u.`Role`;

-- 6. Revenue by payment method
SELECT PaymentMethod, COUNT(*) AS Transactions, SUM(TotalAmount) AS Revenue
  FROM TRANSACTIONS GROUP BY PaymentMethod;

-- 7. Full receipt for a transaction (change the ID)
SELECT t.TransactionID, t.`TimeStamp`, u.FullName AS ServedBy, t.PaymentMethod,
       d.GenericName, b.BatchNumber, s.QuantitySold, b.UnitPrice, s.SubTotal, t.TotalAmount
  FROM TRANSACTIONS t
  JOIN USERS u             ON u.UserID = t.UserID
  JOIN SALES_ITEMS s       ON s.TransactionID = t.TransactionID
  JOIN INVENTORY_BATCHES b ON b.BatchID = s.BatchID
  JOIN DRUGS d             ON d.DrugID = b.DrugID
 WHERE t.TransactionID = 1;

-- 8. Deliveries per supplier
SELECT sp.SupplierName, COUNT(b.BatchID) AS Batches, SUM(b.QuantityReceived) AS UnitsDelivered
  FROM SUPPLIERS sp LEFT JOIN INVENTORY_BATCHES b ON b.SupplierID = sp.SupplierID
 GROUP BY sp.SupplierID, sp.SupplierName;
