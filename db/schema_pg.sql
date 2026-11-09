-- Postgres version of the SouthCity ERP schema (original: schema.sql, SQL Server style).
-- Changes: BIT becomes BOOLEAN. Identifiers stay unquoted so Postgres folds them to lowercase.
-- Run order on Supabase: schema_pg.sql, seed_pg.sql, roles_pg.sql.
-- WARNING: the DROP statements below delete all existing data in these tables.

DROP TABLE IF EXISTS Late_Fee_Penalties;
DROP TABLE IF EXISTS Payments_Received;
DROP TABLE IF EXISTS Payment_Schedules;
DROP TABLE IF EXISTS Sales_Contracts;
DROP TABLE IF EXISTS Units;
DROP TABLE IF EXISTS System_Users;

CREATE TABLE System_Users (
    UserID INT PRIMARY KEY,
    Username VARCHAR(50) NOT NULL UNIQUE,
    FullName VARCHAR(100) NOT NULL,
    Role VARCHAR(30) NOT NULL,               -- 'Sales', 'Finance', 'Auditor', 'SuperAdmin'
    AssignedAgentID INT NULL,                -- SalesAgentID when Role = 'Sales'
    IsActive BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE Units (
    UnitID INT PRIMARY KEY,
    UnitNumber VARCHAR(20) NOT NULL UNIQUE,
    Tower VARCHAR(50) NOT NULL,              -- 'Tower A', 'Tower B'
    UnitType VARCHAR(20) NOT NULL,           -- 'Studio', '2BR', '3BR'
    Floor INT NOT NULL,
    SGA_Area DECIMAL(8, 2) NOT NULL,         -- semi gross area (m2)
    Nett_Area DECIMAL(8, 2) NOT NULL,        -- net area (m2)
    Status VARCHAR(20) NOT NULL DEFAULT 'Vacant' -- 'Vacant', 'Reserved', 'Sold'
);

CREATE TABLE Sales_Contracts (
    ContractID INT PRIMARY KEY,
    ContractNumber VARCHAR(50) NOT NULL UNIQUE,
    UnitID INT NOT NULL UNIQUE,
    CustomerName VARCHAR(150) NOT NULL,
    CustomerNIK VARCHAR(20) NOT NULL,
    SalesAgentID INT NOT NULL,               -- key for Sales row isolation (RBAC)
    BookingDate DATE NOT NULL,
    BasePrice DECIMAL(15, 2) NOT NULL,       -- before VAT
    VAT_Amount DECIMAL(15, 2) NOT NULL,      -- 11%
    TotalPrice DECIMAL(15, 2) NOT NULL,      -- BasePrice + VAT_Amount
    PaymentScheme VARCHAR(30) NOT NULL,      -- 'Hard Cash', 'Installment 24x', 'KPR Express'
    ContractStatus VARCHAR(20) NOT NULL DEFAULT 'Active', -- 'Active', 'Cancelled', 'Completed'
    FOREIGN KEY (UnitID) REFERENCES Units(UnitID)
);

CREATE TABLE Payment_Schedules (
    ScheduleID INT PRIMARY KEY,
    ContractID INT NOT NULL,
    InstallmentNo INT NOT NULL,
    DueDate DATE NOT NULL,
    BillingAmount DECIMAL(15, 2) NOT NULL,
    BillingType VARCHAR(30) NOT NULL,        -- 'Booking Fee', 'Down Payment', 'Monthly Installment', 'Bank Disbursement', 'Hard Cash Settlement'
    Status VARCHAR(20) NOT NULL DEFAULT 'Unpaid', -- 'Unpaid', 'Partially Paid', 'Paid'
    FOREIGN KEY (ContractID) REFERENCES Sales_Contracts(ContractID)
);

CREATE TABLE Payments_Received (
    PaymentID INT PRIMARY KEY,
    ScheduleID INT NOT NULL,
    ContractID INT NOT NULL,                 -- denormalized to aggregate per contract directly
    PaymentDate DATE NOT NULL,
    PaidAmount DECIMAL(15, 2) NOT NULL,
    PaymentMethod VARCHAR(50) NOT NULL,      -- 'Virtual Account BCA', 'Bank Transfer Mandiri', 'Cheque/Giro'
    ReceiptNumber VARCHAR(50) NOT NULL UNIQUE,
    BankReferenceNo VARCHAR(100),
    FOREIGN KEY (ScheduleID) REFERENCES Payment_Schedules(ScheduleID),
    FOREIGN KEY (ContractID) REFERENCES Sales_Contracts(ContractID)
);

CREATE TABLE Late_Fee_Penalties (
    PenaltyID INT PRIMARY KEY,
    ScheduleID INT NOT NULL,
    ContractID INT NOT NULL,
    CalculationDate DATE NOT NULL,
    BaseOverdueAmount DECIMAL(15, 2) NOT NULL,
    DaysOverdue INT NOT NULL,
    DailyRatePermil DECIMAL(5, 4) NOT NULL DEFAULT 0.0010, -- 1 per mille per day
    PenaltyAmount DECIMAL(15, 2) NOT NULL,   -- BaseOverdueAmount * DaysOverdue * DailyRatePermil
    WaiverAmount DECIMAL(15, 2) DEFAULT 0,
    PaidPenalty DECIMAL(15, 2) DEFAULT 0,
    PenaltyStatus VARCHAR(20) NOT NULL DEFAULT 'Outstanding', -- 'Outstanding', 'Settled', 'Waived'
    FOREIGN KEY (ScheduleID) REFERENCES Payment_Schedules(ScheduleID),
    FOREIGN KEY (ContractID) REFERENCES Sales_Contracts(ContractID)
);

CREATE INDEX idx_users_role ON System_Users(Username, Role);
CREATE INDEX idx_units_status ON Units(Status, Tower);
CREATE INDEX idx_contracts_agent ON Sales_Contracts(SalesAgentID);
CREATE INDEX idx_schedules_due ON Payment_Schedules(DueDate, Status);
CREATE INDEX idx_payments_contract ON Payments_Received(ContractID, PaymentDate);
CREATE INDEX idx_penalties_contract ON Late_Fee_Penalties(ContractID, PenaltyStatus);
