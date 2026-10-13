--Create and select the database 
CREATE DATABASE IF NOT EXISTS pharmacy_sales_and_inventory_db;
Use pharmacy_sales_and_inventory_db;

--USERS TABLE
CREATE TABLE USERS(
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    FullName VARCHAR(150) NOT NULL,
    UserName VARCHAR(50) NOT NULL UNIQUE,
    Password VARCHAR(255) NOT NULL,
    Role VARCHAR(50) NOT NULL
);

CREATE TABLE SUPPLIERS(
    SupplierID INT AUTO_INCREMENT PRIMARY KEY,
    SupplierName VARCAR(150) NOT NULL,
    ContactPerson VARCHAR(100),
    PhoneNumber VARCHAR(20),
    Email VARCHAR(100),
    Address TEXT
);

CREATE TABLE CATEGORIES(
    CategoryID INT AUTO_INCREMENT PRIMARY KEY,
    CategoryName VARCHAR(100) NOT NULL,
    Description TEXT
);

CREATE TABLE DRUGS(
    DrugID INT AUTO_INCREMENT PRIMARY KEY,
    CategoryID INT NOT NULL,
    GenericName VARCHAR(150) NOT NULL,
    BrandName VARCHAR(150),
    UnitMeasure FLOAT NOT NULL,
    UnitPrice FLOAT NOT NULL,
    FOREIGN KEY (CategoryID) REFERENCES CATEGORIES(CategoryID)
);


