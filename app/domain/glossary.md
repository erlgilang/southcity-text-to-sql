## Relationships

- units 1:N sales_contracts through sales_contracts.unitid. A unit has at most one contract.
- sales_contracts 1:N payment_schedules through contractid. One row is one billing term.
- payment_schedules 1:N payments_received through scheduleid. payments_received also stores contractid.
- payment_schedules 1:N late_fee_penalties through scheduleid. late_fee_penalties also stores contractid.
- sales_contracts.salesagentid is the sales agent who handles the contract.

## Formulas

- Outstanding principal per contract = SUM(payment_schedules.billingamount) minus SUM(payments_received.paidamount). Compute each sum in its own subquery grouped by contractid, then join the two subqueries to the contract. Joining the tables first and summing afterwards multiplies the numbers.
- Net outstanding penalty = penaltyamount - waiveramount - paidpenalty on late_fee_penalties. For penalties that are not paid yet, filter penaltystatus = 'Outstanding'.
- Penalty = baseoverdueamount x daysoverdue x 0.0010 (1 per mille per day). late_fee_penalties already holds calculated rows, so read them instead of recomputing.
- A billing term is overdue when payment_schedules.duedate is earlier than the date in <today> and its status is 'Unpaid' or 'Partially Paid'. Write the date as a literal, for example DATE '2026-01-31', copied from <today>. Do not use CURRENT_DATE, NOW() or any other clock function.

## Allowed values

- units.status: Vacant, Reserved, Sold
- units.unittype: Studio, 2BR, 3BR
- units.tower: Tower A, Tower B
- payment_schedules.status: Unpaid, Partially Paid, Paid
- payment_schedules.billingtype: Booking Fee, Down Payment, Monthly Installment, Bank Disbursement, Hard Cash Settlement
- sales_contracts.contractstatus: Active, Cancelled, Completed
- sales_contracts.paymentscheme: Hard Cash, Installment 24x, KPR Express
- late_fee_penalties.penaltystatus: Outstanding, Settled, Waived

## Indonesian terms

- jatuh tempo, lewat jatuh tempo, telat bayar: overdue
- tunggakan, sisa tagihan, piutang: outstanding principal
- denda, denda keterlambatan: late fee penalty (late_fee_penalties)
- keringanan denda, diskon denda: waiveramount
- termin, cicilan, angsuran, tagihan: a row of payment_schedules
- pembayaran masuk, kwitansi, realisasi pembayaran: payments_received
- harga jual: totalprice (includes VAT). harga dasar: baseprice. PPN: vat_amount
- pembeli, customer, konsumen: customername
- sales, agen, marketing: salesagentid
- unit kosong: status Vacant. unit terjual: Sold. unit dipesan, booking: Reserved
- cicilan 24x: paymentscheme 'Installment 24x'. tunai, cash: 'Hard Cash'. KPR: 'KPR Express'
- lunas: status Paid. belum lunas: status Unpaid or Partially Paid
- kontrak aktif, batal, selesai: contractstatus Active, Cancelled, Completed
- lantai: floor. luas bersih: nett_area. luas semi gross: sga_area
- tanggal pemesanan: bookingdate
- serah terima unit, BAST: there is no handover table. It can only be judged from unpaid billing terms and outstanding penalties of the contract.

## SQL conventions

- Write table and column names in lowercase without quotes.
- When tables are joined, qualify every column with its table alias. status exists in both units and payment_schedules.
- Match customer names with ILIKE '%name%'. Use = only for codes such as unitnumber and contractnumber.
- Cast with x::date or x::numeric. Only standard aggregate, window, math, text and date functions are available. Regex operators, date(), age(), array functions and generate_series are not.
- Do every calculation in SQL.
- Money columns are numeric(15,2).
