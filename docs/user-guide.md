# PH CAS user guide (short)

- **Invoices.** Make a Sales Invoice; the VAT class comes from the item and can be changed per line; VAT and the customer's withholding are computed. Submit to issue: the BIR serial is taken at submit and the posting date is today. Print gives ORIGINAL and DUPLICATE; the second print says REPRINT. Corrections: a Credit Note (decrease) or a new invoice (increase); an issued invoice is never edited.
- **Collections.** A Payment Entry of type Receive is the Collection Receipt. If the customer paid net of withholding, enter the amount received; the withheld part is booked automatically. Record the 2307 the customer sends as a PH 2307 Received.
- **Bills.** A Purchase Invoice computes input VAT and the withholding from the supplier's category. If you must not withhold, tick the flag and give the reason. Advances to suppliers withhold at payment.
- **Period-end.** PH Compliance Calendar shows what is due. Compute each return's figures (PH Tax Return Figures) and generate the alphalist files (PH Alphalist File); run each file through the BIR Validation module on a Windows PC and record the result; copy the figures into eBIRForms; tick "filed" with the confirmation reference. Issue the 2307s to suppliers from the quarter's bills.
- **Books.** Print or export any book from Reports (PH General Journal and the others); every print carries the BIR header. At year-end, download the e-books pack from the Company form.
- **Closed periods.** Ask the PH Accounting Manager to create an Accounting Period after the quarter is filed; nothing can then be posted into it.

## Getting started: the Sentire Ledger workspace (B34)

The **Sentire Ledger** workspace is the first page after sign-in. Its card "Get to know Sentire Ledger" walks through the six steps a Philippine business takes before issuing its first invoice: set up the Philippine company, confirm the tax rules, print the first BIR invoice, run the 2550Q figures, export the books, build the registration pack. Below the card are shortcuts to the daily documents and the BIR forms, and the books, tax and registration links.

After sign-in you land on Home: a greeting, the six module tiles, the create actions, the "Get to know Sentire Ledger" checklist (until done or dismissed), and the "Business at a glance" cards for the period chosen at the top right (this month, last month, this quarter, this year, all time). Every card opens the list or report behind it. The sidebar collapses with the arrow at its lower edge or with Cmd+/ (Ctrl+/ on Windows).

The sign-in page, the icon in the left rail, the browser tab, the help menu and every email carry the Sentire Ledger mark; the help menu's last item is a contact link to the provider. The About entry under the help menu shows the product version and the open-source licences the system is built on (B38).

Tutorial videos: each step of the standard guides (Make your first sale, Order from your suppliers, and so on) can carry a Sentire Ledger video. The list of steps and their video ids is `ph_cas/setup/data/onboarding_videos.json`; a null entry keeps ERPNext's own video until ours is recorded.
