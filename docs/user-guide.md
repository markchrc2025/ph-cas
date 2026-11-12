# PH CAS user guide (short)

- **Invoices.** Make a Sales Invoice; the VAT class comes from the item and can be changed per line; VAT and the customer's withholding are computed. Submit to issue: the BIR serial is taken at submit and the posting date is today. Print gives ORIGINAL and DUPLICATE; the second print says REPRINT. Corrections: a Credit Note (decrease) or a new invoice (increase); an issued invoice is never edited.
- **Collections.** A Payment Entry of type Receive is the Collection Receipt. If the customer paid net of withholding, enter the amount received; the withheld part is booked automatically. Record the 2307 the customer sends as a PH 2307 Received.
- **Bills.** A Purchase Invoice computes input VAT and the withholding from the supplier's category. If you must not withhold, tick the flag and give the reason. Advances to suppliers withhold at payment.
- **Period-end.** PH Compliance Calendar shows what is due. Compute each return's figures (PH Tax Return Figures) and generate the alphalist files (PH Alphalist File); run each file through the BIR Validation module on a Windows PC and record the result; copy the figures into eBIRForms; tick "filed" with the confirmation reference. Issue the 2307s to suppliers from the quarter's bills.
- **Books.** Print or export any book from Reports (PH General Journal and the others); every print carries the BIR header. At year-end, download the e-books pack from the Company form.
- **Closed periods.** Ask the PH Accounting Manager to create an Accounting Period after the quarter is filed; nothing can then be posted into it.

## Getting started: the Sentire Ledger workspace (B34)

The **Sentire Ledger** workspace is the first page after sign-in. Its card "Get to know Sentire Ledger" walks through the six steps a Philippine business takes before issuing its first invoice: set up the Philippine company, confirm the tax rules, print the first BIR invoice, run the 2550Q figures, export the books, build the registration pack. Below the card are shortcuts to the daily documents and the BIR forms, and the books, tax and registration links.

After sign-in you land on Home: a greeting, the six module tiles, the create actions, the "Get to know Sentire Ledger" checklist (until done or dismissed), and the "Business at a glance" cards for the period chosen at the top right (this month, last month, this quarter, this year, all time). Every card opens the list or report behind it. The column of icons at the far left is the module switcher: hover it and the names appear beside the icons. The menu next to it collapses to an icon rail with the arrow at its lower edge or with Cmd+/ (Ctrl+/ on Windows), and opens again while you hover it.

The sign-in page, the icon in the left rail, the browser tab, the help menu and every email carry the Sentire Ledger mark; the help menu's last item is a contact link to the provider. The About entry under the help menu shows the product version and the open-source licences the system is built on (B38).

Tutorial videos: each step of the standard guides (Make your first sale, Order from your suppliers, and so on) can carry a Sentire Ledger video. The list of steps and their video ids is `ph_cas/setup/data/onboarding_videos.json`; a null entry keeps ERPNext's own video until ours is recorded.

## BIR Returns (B40)

Tax returns > BIR Returns is where a return is made, previewed, exported, filed and kept. One record per company, form and period (period keys: `2026-03` for a month, `2026-Q1` for a quarter, `2026` for a year; a fiscal-year company's quarters count from its fiscal year start on the Company record).

- **What the return still needs** lists, as questions, what is missing on the Company record (TIN, RDO, registered address, contact number and so on) or on the return itself. Open the record it names, fill it in, and the question disappears on the next save. Nothing the books already give is asked for.
- **Figures** shows every item of the form in the paper's order with its kind: books (summed from posted records; Refresh from books brings them in again), typed (yours), derived (computed, never stored). A books figure you change by hand is kept and flagged.
- **Preview (DRAFT)** prints the return on the BIR's own blank with a DRAFT stamp. **Export for eBIRForms** writes the file the offline package loads.
- **Income-tax returns (B44).** The 1701Q and 1702Q take the quarter's sales, cost of sales and itemized deductions from the books, the previous quarters' taxable income and credits from the earlier quarters, and the first three quarters' tax from the filed quarterly returns. The annual 1701, 1701A and 1702-RT take the year's figures the same way; compensation income, the deduction schedules and the NOLCO rows are typed. An individual's Company record needs the individual taxpayer type (single proprietorship or professional) for the 1701 forms.
- **Filing.** Attach the BIR's Tax Return Receipt Confirmation e-mail (the .eml, a PDF print of it, or its text) with Attach BIR confirmation; it is checked against the return (sender, form, TIN, branch, period, received time). Then Submit: the return is filed, read-only, the taxpayer block is kept as it was that day, the clear copy (as filed) is attached, and the figures go to Tax Return Figures for the calendar and the dashboard. A System Manager may file without the e-mail by giving an override reason, which is logged.
- **After filing** nothing changes. A manager opens an amendment (Open amendment, with a reason): a new draft with the same figures, the Amended Return box ticked, linked to the original, which stays filed and readable.

Until a form's engine is built, its return says so under needs and cannot be filed.
