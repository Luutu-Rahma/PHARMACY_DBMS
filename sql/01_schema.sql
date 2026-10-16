-- ============================================================
-- 01_schema.sql  -  PharmaFlow: Pharmacy Inventory & Sales DBMS
-- Group 16
-- Creates the database and all 7 tables (matches the ERD and
-- data dictionary).
-- ============================================================
CREATE DATABASE IF NOT EXISTS pharmacy_sales_and_inventory_db;
USE pharmacy_sales_and_inventory_db;

-- 1. USERS: staff accounts + one of the four system roles
CREATE TABLE IF NOT EXISTS USERS (
    UserID    INT AUTO_INCREMENT PRIMARY KEY,
    FullName  VARCHAR(150) NOT NULL,
    UserName  VARCHAR(50)  NOT NULL UNIQUE,
    Password  VARCHAR(255) NOT NULL,          -- store a hash, never plain text
    `Role`    VARCHAR(50)  NOT NULL,
    CONSTRAINT chk_user_role CHECK
        (`Role` IN ('Admin','InventoryManager','Pharmacist','Cashier'))
);

-- 2. CATEGORIES: logical drug groups
CREATE TABLE IF NOT EXISTS CATEGORIES (
    CategoryID   INT AUTO_INCREMENT PRIMARY KEY,
    CategoryName VARCHAR(100) NOT NULL UNIQUE,
    Description  TEXT
);

-- 3. SUPPLIERS: vendors who deliver batches
CREATE TABLE IF NOT EXISTS SUPPLIERS (
    SupplierID    INT AUTO_INCREMENT PRIMARY KEY,
    SupplierName  VARCHAR(150) NOT NULL,
    ContactPerson VARCHAR(100),
    PhoneNumber   VARCHAR(20),
    Email         VARCHAR(100),
    Address       TEXT
);

-- 4. DRUGS: master catalogue (Category 1 : M Drugs)
CREATE TABLE IF NOT EXISTS DRUGS (
    DrugID      INT AUTO_INCREMENT PRIMARY KEY,
    CategoryID  INT NOT NULL,
    GenericName VARCHAR(150) NOT NULL,
    BrandName   VARCHAR(150),
    UnitMeasure VARCHAR(50)  NOT NULL,        -- e.g. tablets, bottle, capsules
    UnitPrice   DECIMAL(12,2) NOT NULL,       -- standard base selling price
    CONSTRAINT chk_drug_price CHECK (UnitPrice >= 0),
    CONSTRAINT fk_drug_category FOREIGN KEY (CategoryID)
        REFERENCES CATEGORIES(CategoryID)
);

-- 5. INVENTORY_BATCHES: physical stock (Drug 1 : M Batches, Supplier 1 : M Batches)
CREATE TABLE IF NOT EXISTS INVENTORY_BATCHES (
    BatchID          INT AUTO_INCREMENT PRIMARY KEY,
    DrugID           INT NOT NULL,
    SupplierID       INT NOT NULL,
    BatchNumber      VARCHAR(50) NOT NULL,
    QuantityReceived INT NOT NULL,
    QuantityLeft     INT NOT NULL,
    MFD              DATE NOT NULL,
    ExpiryDate       DATE NOT NULL,
    UnitPrice        DECIMAL(12,2) NOT NULL,  -- selling price for THIS batch
    CONSTRAINT uq_drug_batch   UNIQUE (DrugID, BatchNumber),
    CONSTRAINT chk_qty_rec     CHECK (QuantityReceived > 0),
    CONSTRAINT chk_qty_left    CHECK (QuantityLeft >= 0 AND QuantityLeft <= QuantityReceived),
    CONSTRAINT chk_dates       CHECK (ExpiryDate > MFD),
    CONSTRAINT chk_batch_price CHECK (UnitPrice >= 0),
    CONSTRAINT fk_batch_drug     FOREIGN KEY (DrugID)     REFERENCES DRUGS(DrugID),
    CONSTRAINT fk_batch_supplier FOREIGN KEY (SupplierID) REFERENCES SUPPLIERS(SupplierID)
);
-- Speeds up the FIFO lookup (earliest expiry first, per drug)
CREATE INDEX idx_batches_fifo ON INVENTORY_BATCHES (DrugID, ExpiryDate);

-- 6. TRANSACTIONS: checkout header, tied to the staff member (User 1 : M Transactions)
CREATE TABLE IF NOT EXISTS TRANSACTIONS (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    UserID        INT NOT NULL,
    `TimeStamp`   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    TotalAmount   DECIMAL(12,2) NOT NULL DEFAULT 0,   -- maintained by trigger
    PaymentMethod VARCHAR(50) NOT NULL,
    CONSTRAINT chk_payment CHECK (PaymentMethod IN ('Cash','Mobile Money')),
    CONSTRAINT fk_txn_user FOREIGN KEY (UserID) REFERENCES USERS(UserID)
);

-- 7. SALES_ITEMS: junction Transactions <-> Batches
CREATE TABLE IF NOT EXISTS SALES_ITEMS (
    SalesItemID   INT AUTO_INCREMENT PRIMARY KEY,
    TransactionID INT NOT NULL,
    BatchID       INT NOT NULL,
    QuantitySold  INT NOT NULL,
    SubTotal      DECIMAL(12,2) NOT NULL DEFAULT 0,   -- set by trigger
    CONSTRAINT chk_qty_sold CHECK (QuantitySold > 0),
    CONSTRAINT fk_item_txn   FOREIGN KEY (TransactionID) REFERENCES TRANSACTIONS(TransactionID)
        ON DELETE CASCADE,
    CONSTRAINT fk_item_batch FOREIGN KEY (BatchID) REFERENCES INVENTORY_BATCHES(BatchID)
);
