# Spec: Export invoices as CSV

status: ready
author: billing team · reviewed by cold read round 2

## Problem

Accountants copy invoice rows by hand from the web page into their spreadsheet every
month. It takes about 40 minutes per client and typos slip in. They need a file.

## Out of scope

- PDF export, scheduled or emailed exports.
- Changing how invoices are stored.
- Exports for more than one client at once.

## Glossary

- **Client admin**: a user with the `billing:admin` role for one client account.
- **Issued date**: the date an invoice was sent, stored in UTC, shown in the client's time zone.

## Requirements

- R1: A client admin MUST be able to download all invoices issued in a chosen date range as one CSV file.
  - ex R1.a: given 3 invoices issued 2026-03-01..2026-03-31, when the admin exports March 2026, then the file has 1 header row and 3 data rows.
  - ex R1.b: given no invoices in the range, when the admin exports, then the file has only the header row and the page says "0 invoices".
- R2: The range MUST be at most 366 days; a longer range MUST be refused before any work starts.
  - ex R2.a: given a range of 367 days, when the admin exports, then the request is refused with message "Pick 366 days or fewer" and no file is made.
- R3: Columns MUST be, in order: number, issued_date (YYYY-MM-DD in the client's time zone), customer, net, tax, total, currency.
  - ex R3.a: given an invoice issued 2026-03-31T23:30Z for a client in UTC+2, when exported, then issued_date is 2026-04-01.
- R4: Money MUST be written with a dot decimal separator and exactly 2 decimals, without thousands separators.
  - ex R4.a: given a total of 1234.5 EUR, when exported, then the total cell is 1234.50.
- R5: Users without the client admin role MUST NOT be able to export; the button SHOULD be hidden for them.
  - ex R5.a: given a viewer-role user, when they call the export URL directly, then they get HTTP 403 and no file.

## Decisions

- D1: UTF-8 with a byte-order mark, because the accountants open files in Excel on Windows.
- D2: Synchronous download up to 366 days; measured worst client is 9,800 invoices in 2.1 s.
