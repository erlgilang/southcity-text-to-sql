-- Seed data copied from schema.sql. Only IsActive changed (1 became TRUE).

-- Users for the RBAC switcher.
INSERT INTO System_Users (UserID, Username, FullName, Role, AssignedAgentID, IsActive) VALUES
(1, 'sales_bambang', 'Bambang Pamungkas', 'Sales', 101, TRUE),
(2, 'sales_dewi', 'Dewi Lestari', 'Sales', 102, TRUE),
(3, 'sales_reza', 'Reza Rahadian', 'Sales', 103, TRUE),
(4, 'finance_hendra', 'Hendra Setiawan', 'Finance', NULL, TRUE),
(5, 'auditor_maya', 'Maya Kusuma', 'Auditor', NULL, TRUE);

-- 12 units across both towers, mixed types, floors and statuses.
INSERT INTO Units (UnitID, UnitNumber, Tower, UnitType, Floor, SGA_Area, Nett_Area, Status) VALUES
(1,  'A-0101', 'Tower A', 'Studio', 1,  24.50, 20.00, 'Sold'),
(2,  'A-0502', 'Tower A', '2BR',    5,  48.00, 41.50, 'Vacant'),
(3,  'A-1205', 'Tower A', '2BR',    12, 52.00, 45.00, 'Sold'),
(4,  'A-1508', 'Tower A', '3BR',    15, 85.00, 74.00, 'Sold'),
(5,  'A-2001', 'Tower A', 'Studio', 20, 24.50, 20.00, 'Vacant'),
(6,  'B-0301', 'Tower B', 'Studio', 3,  24.50, 20.00, 'Vacant'),
(7,  'B-0703', 'Tower B', '2BR',    7,  50.00, 43.00, 'Vacant'),
(8,  'B-1008', 'Tower B', '3BR',    10, 85.00, 74.00, 'Reserved'),
(9,  'B-1602', 'Tower B', '2BR',    16, 52.00, 45.00, 'Sold'),
(10, 'B-1805', 'Tower B', 'Studio', 18, 25.00, 20.50, 'Sold'),
(11, 'B-2101', 'Tower B', '3BR',    21, 92.00, 80.00, 'Sold'),
(12, 'B-2202', 'Tower B', '2BR',    22, 52.00, 45.00, 'Vacant');

-- 101 Budi Santoso (agent 101): Installment 24x
-- 102 Siti Rahma (agent 102): KPR Express
-- 103 Robert Tan (agent 101): Hard Cash, fully paid
-- 104 Linda Wijaya (agent 103): Installment 24x, heavy penalties
-- 105 Ahmad Farhan (agent 102): KPR Express, late down payment
-- 106 Christine Hartono (agent 103): Installment 24x, penalty settled
INSERT INTO Sales_Contracts (ContractID, ContractNumber, UnitID, CustomerName, CustomerNIK, SalesAgentID, BookingDate, BasePrice, VAT_Amount, TotalPrice, PaymentScheme, ContractStatus) VALUES
(101, 'CTR-SC-2026-001', 1,  'Budi Santoso',      '3171012345670001', 101, '2026-01-10', 900000000.00,   99000000.00,  999000000.00,  'Installment 24x', 'Active'),
(102, 'CTR-SC-2026-002', 3,  'Siti Rahma',        '3171098765430002', 102, '2026-02-15', 1400000000.00, 154000000.00, 1554000000.00, 'KPR Express',     'Active'),
(103, 'CTR-SC-2026-003', 4,  'Robert Tan',        '3171055544430003', 101, '2026-01-20', 2100000000.00, 231000000.00, 2331000000.00, 'Hard Cash',       'Completed'),
(104, 'CTR-SC-2026-004', 9,  'Linda Wijaya',      '3275088899910004', 103, '2026-02-01', 1350000000.00, 148500000.00, 1498500000.00, 'Installment 24x', 'Active'),
(105, 'CTR-SC-2026-005', 10, 'Ahmad Farhan',      '3174066611120005', 102, '2026-03-05', 650000000.00,   71500000.00,  721500000.00,  'KPR Express',     'Active'),
(106, 'CTR-SC-2026-006', 11, 'Christine Hartono', '3173022233340006', 103, '2026-01-15', 2300000000.00, 253000000.00, 2553000000.00, 'Installment 24x', 'Active');

-- Billing terms. KPR disbursements fall in 2027.
INSERT INTO Payment_Schedules (ScheduleID, ContractID, InstallmentNo, DueDate, BillingAmount, BillingType, Status) VALUES
(1001, 101, 1, '2026-02-10', 50000000.00,  'Booking Fee',          'Paid'),
(1002, 101, 2, '2026-03-10', 40000000.00,  'Monthly Installment',   'Partially Paid'),
(1003, 101, 3, '2026-04-10', 40000000.00,  'Monthly Installment',   'Unpaid'),
(1005, 102, 1, '2026-02-20', 100000000.00, 'Down Payment',         'Paid'),
(1006, 102, 2, '2027-12-20', 1454000000.00,'Bank Disbursement',    'Unpaid'),
(1007, 103, 1, '2026-01-25', 50000000.00,  'Booking Fee',          'Paid'),
(1008, 103, 2, '2026-02-25', 2281000000.00,'Hard Cash Settlement', 'Paid'),
(1009, 104, 1, '2026-02-15', 50000000.00,  'Booking Fee',          'Paid'),
(1010, 104, 2, '2026-03-15', 60000000.00,  'Monthly Installment',   'Unpaid'),
(1011, 104, 3, '2026-04-15', 60000000.00,  'Monthly Installment',   'Unpaid'),
(1012, 105, 1, '2026-03-10', 30000000.00,  'Booking Fee',          'Paid'),
(1013, 105, 2, '2026-04-10', 50000000.00,  'Down Payment',         'Partially Paid'),
(1014, 105, 3, '2027-12-10', 641500000.00, 'Bank Disbursement',    'Unpaid'),
(1015, 106, 1, '2026-01-20', 50000000.00,  'Booking Fee',          'Paid'),
(1016, 106, 2, '2026-02-20', 100000000.00, 'Down Payment',         'Paid'),
(1017, 106, 3, '2026-03-20', 100000000.00, 'Monthly Installment',   'Paid');

-- Cash received per schedule.
INSERT INTO Payments_Received (PaymentID, ScheduleID, ContractID, PaymentDate, PaidAmount, PaymentMethod, ReceiptNumber, BankReferenceNo) VALUES
(501, 1001, 101, '2026-02-09', 50000000.00,   'Virtual Account BCA',   'REC-202602-001', 'BCAVA-882910'),
(502, 1002, 101, '2026-03-15', 15000000.00,   'Virtual Account BCA',   'REC-202603-044', 'BCAVA-882911'),
(503, 1005, 102, '2026-02-19', 100000000.00,  'Bank Transfer Mandiri', 'REC-202602-019', 'MND-992100'),
(504, 1007, 103, '2026-01-24', 50000000.00,   'Bank Transfer Mandiri', 'REC-202601-008', 'MND-881230'),
(505, 1008, 103, '2026-02-24', 2281000000.00, 'Cheque/Giro',          'REC-202602-099', 'GIRO-BCA-00129'),
(506, 1009, 104, '2026-02-14', 50000000.00,   'Virtual Account BCA',   'REC-202602-025', 'BCAVA-883301'),
(507, 1012, 105, '2026-03-09', 30000000.00,   'Virtual Account BCA',   'REC-202603-011', 'BCAVA-884100'),
(508, 1013, 105, '2026-04-18', 20000000.00,   'Virtual Account BCA',   'REC-202604-032', 'BCAVA-884101'),
(509, 1015, 106, '2026-01-19', 50000000.00,   'Bank Transfer Mandiri', 'REC-202601-005', 'MND-771120'),
(510, 1016, 106, '2026-02-19', 100000000.00,  'Bank Transfer Mandiri', 'REC-202602-015', 'MND-771125'),
(511, 1017, 106, '2026-04-05', 100000000.00,  'Virtual Account BCA',   'REC-202604-002', 'BCAVA-885501');

-- 9001 Budi: 25M overdue 30 days = 750k, waiver 150k, net 600k
-- 9002 Linda: 60M x 45 days x 0.0010 = 2.7M
-- 9003 Linda: 60M x 15 days x 0.0010 = 900k
-- 9004 Ahmad: 30M x 20 days x 0.0010 = 600k
-- 9005 Christine: 100M x 16 days = 1.6M, fully paid (Settled)
INSERT INTO Late_Fee_Penalties (PenaltyID, ScheduleID, ContractID, CalculationDate, BaseOverdueAmount, DaysOverdue, DailyRatePermil, PenaltyAmount, WaiverAmount, PaidPenalty, PenaltyStatus) VALUES
(9001, 1002, 101, '2026-04-10', 25000000.00, 30, 0.0010, 750000.00,  150000.00, 0.00,       'Outstanding'),
(9002, 1010, 104, '2026-04-30', 60000000.00, 45, 0.0010, 2700000.00, 0.00,      0.00,       'Outstanding'),
(9003, 1011, 104, '2026-04-30', 60000000.00, 15, 0.0010, 900000.00,  0.00,      0.00,       'Outstanding'),
(9004, 1013, 105, '2026-04-30', 30000000.00, 20, 0.0010, 600000.00,  0.00,      0.00,       'Outstanding'),
(9005, 1017, 106, '2026-04-05', 100000000.00,16, 0.0010, 1600000.00, 0.00,      1600000.00, 'Settled');
