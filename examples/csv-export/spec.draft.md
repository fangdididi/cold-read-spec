# Spec: Export invoices as CSV (first draft, before the cold read)

status: ready

## Problem

Accountants copy invoice rows by hand into spreadsheets. They need a file.

## Requirements

- R1: Admins MUST be able to export invoices for a date range as CSV quickly.
  - ex R1.a: given 3 invoices in March, when the admin exports March, then the file has 3 data rows.
- R2: Long ranges should be handled appropriately.
- R3: Columns: number, date, customer, net, tax, total, currency.
  - ex R3.a: export one invoice and look at the columns.

## Open questions

- Q1: Which encoding does Excel need?
