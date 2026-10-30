-- Additive, non-destructive PharmaFlow schema for the database selected by DATABASE_URL.
-- Run only after checking that the configured Aiven database does not already contain these tables.
-- This file never creates/switches databases, drops objects, or inserts sample data.
CREATE TABLE IF NOT EXISTS USERS (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    FullName VARCHAR(150) NOT NULL,
    UserName VARCHAR(50) NOT NULL UNIQUE,
    Password VARCHAR(255) NOT NULL,
    `Role` VARCHAR(50) NOT NULL,
    CONSTRAINT chk_user_role CHECK (
        `Role` IN (
            'Admin',
            'InventoryManager',
            'Pharmacist',
            'Cashier'
        )
    )
) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS CATEGORIES (
    CategoryID INT AUTO_INCREMENT PRIMARY KEY,
    CategoryName VARCHAR(100) NOT NULL UNIQUE,
    Description TEXT
) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS SUPPLIERS (
    SupplierID INT AUTO_INCREMENT PRIMARY KEY,
    SupplierName VARCHAR(150) NOT NULL,
    ContactPerson VARCHAR(100),
    PhoneNumber VARCHAR(20),
    Email VARCHAR(100),
    Address TEXT
) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS DRUGS (
    DrugID INT AUTO_INCREMENT PRIMARY KEY,
    CategoryID INT NOT NULL,
    GenericName VARCHAR(150) NOT NULL,
    BrandName VARCHAR(150),
    UnitMeasure VARCHAR(50) NOT NULL,
    UnitPrice DECIMAL(12, 2) NOT NULL,
    CONSTRAINT chk_drug_price CHECK (UnitPrice >= 0),
    CONSTRAINT fk_drug_category FOREIGN KEY (CategoryID) REFERENCES CATEGORIES(CategoryID)
) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS INVENTORY_BATCHES (
    BatchID INT AUTO_INCREMENT PRIMARY KEY,
    DrugID INT NOT NULL,
    SupplierID INT NOT NULL,
    BatchNumber VARCHAR(50) NOT NULL,
    QuantityReceived INT NOT NULL,
    QuantityLeft INT NOT NULL,
    MFD DATE NOT NULL,
    ExpiryDate DATE NOT NULL,
    UnitPrice DECIMAL(12, 2) NOT NULL,
    CONSTRAINT uq_drug_batch UNIQUE (DrugID, BatchNumber),
    CONSTRAINT chk_qty_rec CHECK (QuantityReceived > 0),
    CONSTRAINT chk_qty_left CHECK (
        QuantityLeft >= 0
        AND QuantityLeft <= QuantityReceived
    ),
    CONSTRAINT chk_dates CHECK (ExpiryDate > MFD),
    CONSTRAINT chk_batch_price CHECK (UnitPrice >= 0),
    CONSTRAINT fk_batch_drug FOREIGN KEY (DrugID) REFERENCES DRUGS(DrugID),
    CONSTRAINT fk_batch_supplier FOREIGN KEY (SupplierID) REFERENCES SUPPLIERS(SupplierID),
    INDEX idx_batches_fifo (DrugID, ExpiryDate)
) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS TRANSACTIONS (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    `TimeStamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    TotalAmount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    PaymentMethod VARCHAR(50) NOT NULL,
    CONSTRAINT chk_payment CHECK (PaymentMethod IN ('Cash', 'Mobile Money')),
    CONSTRAINT fk_txn_user FOREIGN KEY (UserID) REFERENCES USERS(UserID)
) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS SALES_ITEMS (
    SalesItemID INT AUTO_INCREMENT PRIMARY KEY,
    TransactionID INT NOT NULL,
    BatchID INT NOT NULL,
    QuantitySold INT NOT NULL,
    SubTotal DECIMAL(12, 2) NOT NULL DEFAULT 0,
    CONSTRAINT chk_qty_sold CHECK (QuantitySold > 0),
    CONSTRAINT fk_item_txn FOREIGN KEY (TransactionID) REFERENCES TRANSACTIONS(TransactionID) ON DELETE CASCADE,
    CONSTRAINT fk_item_batch FOREIGN KEY (BatchID) REFERENCES INVENTORY_BATCHES(BatchID)
) ENGINE = InnoDB;