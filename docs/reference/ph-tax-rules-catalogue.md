# Philippine tax rules for the CAS: MSME catalogue, v1.1 (26 Oct 2026)

Prepared by Claude at the owner's request: the Philippine tax rules the firm's CAS must build in, so it is ready to use for MSMEs out of the box.
- **What the CAS does with them:** applies every rule to the books (VAT, percentage tax, withholding, income tax) and produces the figures and files each return needs.
- **What it doesn't do:** file returns. Filing stays outside it.

**Status: draft for CPA sign-off.**
- Every rule is cited to its issuance, and the **Check** column marks where this draft is less than certain.
- v1.1 has been through an independent check against the sources. It fixed:
  - the retention period (EOPT: five years);
  - the senior citizen/PWD 5% cap (₱2,500 a week);
  - the e-invoicing coverage reading;
  - the correction rule for e-invoices.
- It also added the changes v1 missed, including RR 6-2026 (withholding shown on invoices) and RR 9-2025 (VAT on purchases from ecozone enterprises).
- No rule goes into code until the firm's CPA confirms it.

Companion docs: `claude/ph-cas-build-plan-2026-10-24.md` (the build) and `claude/erpnext-bir-cas-review-2026-10-24.md` (what ERPNext does today).

## How the rules live in the system
- **Rules are dated data, not code.** One table holds every rule, with its rate, base, ATC, return line, legal basis, and effective-from and effective-to dates.
  - Each computation uses the rule in force on the transaction date.
  - A rate change is a new row, so past periods keep computing correctly.
- **Five places where rules apply:**
  - the client's tax profile;
  - sales invoices;
  - supplier bills and payments;
  - period-end;
  - reports and BIR files.
- **Every rule has a test** with worked figures. Where a return exists, the same figures are entered in eBIRForms in its normal way, and the tax due must match. For 2020-2021 losses, the RMC 81-2026 workaround applies, because eBIRForms accepts only three years of NOLCO.
- **Life cycle of a rule:** draft → confirmed by the CPA → coded.

## A. Client tax profile (set at onboarding; drives everything else)
| Setting | Options and effect | Basis | Check |
|---|---|---|---|
| Taxpayer classification | **Thresholds:** Micro: gross sales < ₱3M. Small: ₱3M to < ₱20M. Medium: ₱20M to < ₱1B. Large: ≥ ₱1B. **E-invoicing:** micro taxpayers are excluded. Non-micro taxpayers are covered if they fall in a listed category. One category is "taxpayers using CAS or CBA with Accounting Records (with electronic invoicing), and other invoicing software", so a non-micro client invoicing from this CAS should plan to be covered: e-invoices by 31 Dec 2026, then the PTI and EIS certification. **Also decides** whether an individual may file 1701-MS. | RR 8-2024; RMC 98-2026 Secs. III-IV; RMC 20-2026; RMC 37-2026 | RDO: coverage of non-micro CAS users |
| Business tax | VAT-registered (12%), required above ₱3M gross sales or receipts. Non-VAT: percentage tax 3%. Individuals on the 8% option pay it in lieu of percentage tax and graduated income tax. | NIRC 106, 108, 109(BB), 116, as amended by TRAIN |: |
| Income tax, corporation | **Rate:** 25% regular; 20% if net taxable income ≤ ₱5M and total assets ≤ ₱100M, excluding the land of the office or plant. **MCIT:** 2% of gross income from the 4th taxable year after operations began (1% from 1 Jul 2020 to 30 Jun 2023). The higher of regular tax and MCIT is due, and excess MCIT carries forward 3 years against regular tax. | CREATE (RA 11534); NIRC 27(E) | MCIT carry-forward from a secondary source |
| Income tax, individual | **Graduated table** (2023 onwards: 0% up to ₱250k; 15%, 20%, 25%, 30% and 35% bands with breaks at ₱400k, ₱800k, ₱2M and ₱8M). **Or the 8% option**, if gross sales or receipts and other non-operating income are ≤ ₱3M: purely self-employed individuals pay 8% on the amount above ₱250,000; mixed-income earners pay 8% on all business gross, without the ₱250k reduction. | TRAIN (RA 10963); RR 8-2018 |: |
| Deduction method | OSD (40%) or itemized | NIRC 34(L) |: |
| Withholding agent | Every business withholds on the listed income payments: rent, professional fees, contractors and the rest. EOPT's proposed exemption for micro taxpayers was vetoed. Top Withholding Agents (designated by the BIR) also withhold on goods and services. | RR 2-98 as amended; RR 31-2020; RR 24-2025; RA 11976 veto message |: |
| Registration data | TIN with 5-digit branch code; RDO; registered name and address; calendar or fiscal year; registered activities | RR 7-2024; RMC 36-2026 |: |
| Special regimes | **Discounts:** business covered by the senior citizen/PWD discounts (restaurant, pharmacy, hotel, transport, recreation). **Platforms:** seller on e-marketplaces. **Zero-rating:** exporter, or supplier to registered business enterprises; under CREATE MORE the sale must be "directly attributable" to the registered project, supported by the IPA's VAT Zero-Rating Certificate. **RBE purchases:** buyer from registered business enterprises (see C). | RA 9994; RA 10754; RR 5-2025; RR 10-2025; RMC 66-2025; RR 9-2025 |: |
| Audit requirement | Gross annual sales or receipts exceeding ₱3M: financial statements audited by an independent CPA | NIRC 232 as amended by TRAIN | Statute text not retrieved |

## B. Sales and invoices
| Rule | What the system does | Basis | Check |
|---|---|---|---|
| When an invoice is issued | **VAT-registered:** an invoice for every sale, goods or services. **Non-VAT:** an invoice for each sale of ₱500 or more, whenever the buyer asks, or one end-of-day invoice for smaller sales once they add up to ₱500. **Buyer details:** registered name, address and TIN are required for sales of ₱1,000 or more to a VAT-registered buyer; a buyer needs its name and TIN on the invoice to claim input VAT. | RA 11976 Secs. 113(B), 237; RR 7-2024 (from 27 Apr 2024); RMC 77-2024 |: |
| Supplementary documents | Collection and delivery receipts are supplementary only. They carry "THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX". | RR 7-2024 Annex B; RMC 5-2021 Annex B |: |
| Withholding shown on the invoice | From 16 Oct 2026, the invoice shows the creditable withholding tax as a separate item, "Less: Withholding Tax", where applicable. The system computes it from the customer's withholding profile (ATC and rate) and shows the net amount due. | RR 6-2026 (published 1 Oct 2026), amending RR 7-2024 Sec. 6(B) | What "applicable" covers; transition for system-generated invoices |
| VAT class on every line | **VATable** 12%. **Zero-rated:** export, or local sales to registered enterprises with the certificate. **Exempt:** the Sec. 109 item is recorded. **Sale to government.** Separate invoices are marked "VAT-Exempt Sale" or "Zero-rated Sale"; mixed invoices show the VATable, exempt and zero-rated amounts separately. | NIRC 106-109; RR 7-2024 Annex B; CREATE MORE |: |
| Sales to government | Full 12% output VAT. The government withholds 5% creditable VAT, which is credited against output VAT on the 2307 received (ATC WV010 goods, WV020 services). The government also withholds creditable income tax (reported 1% goods, 2% services) and, from non-VAT sellers, 3% percentage tax. | TRAIN; RR 13-2018 (creditable from 1 Jan 2021) | Income-tax and percentage-tax rates and ATCs come from secondary sources |
| Non-VAT sellers | No VAT on the invoice. Percentage tax 3% of gross sales (ATC PT010), with sales subject to percentage tax shown separately from exempt sales. "EXEMPT" if neither VAT nor percentage tax applies. | NIRC 116; RR 7-2024 Annex B |: |
| VAT on services is accrual-based | Output VAT at invoice (the sale), not at collection, for sales from 27 Apr 2024. Services rendered before that and collected later: output VAT when collected. | RA 11976; RR 3-2024 |: |
| Corrections | **Decrease:** a credit note referencing the original invoice. **Increase:** a new invoice (for e-invoices, RMC 98-2026 Sec. IV.8). An issued invoice is never edited. The BIR's detailed sales-adjustment rules await a separate issuance. | RR 7-2024; RMC 98-2026 Sec. IV.8 | Debit notes for non-e-invoices |
| Output VAT credit on uncollected receivables (optional) | **When:** in the quarter after the agreed credit term lapses, and only that quarter. **Conditions:** sale after 27 Apr 2024; credit term on the invoice or another written document; VAT shown and declared; buyer named in the summary list of sales; not claimed as a bad debt. **Records:** the seller's copy is stamped "Claimed Output VAT Credit"; a later collection is declared again and the copy stamped "Recovered". | RR 3-2024; RMC 65-2024; RMC 68-2024 |: |
| Senior citizen and PWD discounts | **20% discount plus VAT exemption** on covered goods and services (restaurants, medicines, hotels, transport, recreation), for the holder's exclusive use. The 20% is taken on the VAT-exclusive price. The invoice shows the gross price and the discount separately, marked VAT-exempt. **Records per sale:** holder's name, OSCA/PWD ID, discount, date and invoice number. **Tax treatment:** the discount is deducted from gross income, which rules out OSD; input VAT on these exempt sales is not creditable. **5% special discount** on basic necessities and prime commodities, for seniors and PWDs: purchases capped at ₱2,500 a week (discount up to ₱125), no carry-over, no VAT exemption, not applicable to BMBEs and cooperatives, from 25 Mar 2024. | RA 9994, RR 7-2010, RMC 38-2012; RA 10754, RR 5-2017, RR 9-2019; DTI-DA-DOE Joint Administrative Order (25 Mar 2024) | Order number; computation base from a secondary source |
| Platform sales | From 14 Mar 2025: e-marketplaces and digital financial services providers withhold 0.5% of gross remittances to sellers (WI820/WC820, WI830/WC830; WI760/WC760 dropped). Credit card companies withhold 0.5% of the gross amount (WI156/WC156). The seller books both as creditable tax. | RR 16-2023; RR 5-2025; RMO 18-2025 | RR 16-2023's ₱500,000 threshold and sworn declaration: PayMongo says they remain; RR 5-2025's text not retrieved |
| Tax withheld by customers | Each 2307 received is captured against the invoice: EWT is an income-tax credit, VAT withheld a VAT credit, percentage tax withheld a percentage-tax credit. These feed the SAWT. | RR 2-98 as amended |: |

## C. Purchases, bills and payments
| Rule | What the system does | Basis | Check |
|---|---|---|---|
| Input VAT only from a proper VAT invoice | No input VAT on supplementary documents or on purchases from non-VAT sellers | RR 7-2024; RR 11-2024; RMC 77-2024 |: |
| Capital goods | Input VAT claimed in full at purchase from 1 Jan 2022. Deferred balances from earlier purchases are amortized as scheduled, and the rest is claimed if the asset is sold within 5 years. | TRAIN; RMC 21-2022 |: |
| Mixed sales | Input VAT directly attributable to exempt sales is not creditable. Common input VAT is allowed × (taxable + zero-rated sales) ÷ total sales. | NIRC 110; RR 16-2005 | Secondary source |
| Unpaid payables | If a supplier claims output VAT credit on an invoice the buyer hasn't paid, the buyer reverses that input VAT (2550Q item 55) and adds it back on payment (item 58) | RR 3-2024; RMC 65-2024; RMC 68-2024 |: |
| Expanded withholding on payments | Applied automatically on the bill from the supplier's profile. **Professional fees:** individuals 5% (gross ≤ ₱3M) or 10% (> ₱3M, or VAT-registered); juridical 10% (≤ ₱720k) or 15%. **Rentals** 5% (personal property: above ₱10k a year). **Contractors** 2%. **Top Withholding Agents also withhold** 1% on goods and 2% on services. **Reduced 0.5%:** on goods for wholesale bought from manufacturers or direct importers of motor vehicles, medicines and fuels. It applies from 10 Oct 2025, once the supplier has given the required documents; its codes (WI/WC 840-860) exist from 27 Oct 2025. | RR 2-98 as amended by RR 11-2018, RR 31-2020, RR 24-2025; RMO 46-2025; RMC 79-2026 | ATC per category (WI010/WI011, WC010/WC011, WI100/WC100, WI120/WC120, WI158/WC158, WI160/WC160) against the 2307 schedule |
| When to withhold | When the amount becomes payable, is accrued or recorded, or the supplier issues its invoice (the invoice date), whichever comes first. Payment alone is no longer the trigger. | RA 11976; RR 4-2024 |: |
| Expense without withholding | From taxable year 2024 the expense stays deductible (Sec. 34(K) repealed), but the duty to withhold and its penalties remain, so the system flags it | RA 11976; RMC 60-2024 |: |
| Certificates to payees | One 2307 per payee per quarter, by the 20th day after the quarter, or with the payment if the payee asks | RR 2-98 as amended by RR 11-2018 |: |
| Digital services from non-resident providers (ads, SaaS) | Any buyer engaged in business withholds the 12% VAT and remits it on 1600-VT within 10 days after the month, with its monthly alphalist (ATC WV080 private, WV090 government). A VAT-registered buyer claims it as input VAT, supported by the filed return; a non-VAT buyer treats it as cost. Applies to services from 2 Jun 2025. | RA 12023; RR 3-2025; RR 14-2025; RMC 47-2025; RMC 49-2025; RMC 55-2026; RMC 59-2026 |: |
| Purchases from registered business enterprises (ecozones, BOI) | **The seller's invoice** shows "VAT on Local Sales" and leaves it out of the amount due. **The business buyer remits the VAT:** goods on Form 0605 per transaction, before the goods are released; services on 1600-VT by the 10th of the next month. **Input VAT:** claimable only after payment; non-VAT buyers treat it as cost. | RR 9-2025 (27 Feb 2025) | Reported RR 1-2026 amendment and ATC WV110 not verified |
| Interest income on deposits | Recorded net of the 20% final tax the bank withholds, and excluded from taxable income. From 1 Jul 2025 FCDU interest is also 20% and long-term deposits are no longer exempt, except instruments issued before that date and held unchanged to maturity. | NIRC 24(B), 27(D); CMEPA (RA 12214); RR 20-2025; RR 21-2025 |: |

## D. Period-end: the figures for each return
| Return | What the system computes | Basis | Check |
|---|---|---|---|
| VAT, quarterly (2550Q version 2024; no monthly 2550M from 2023) | **Starts from** output VAT by class. **Less:** input VAT (current, plus the pre-2022 deferred schedule); the 5% VAT withheld by government; output VAT credit on uncollected receivables (item 35). **Plus:** recoveries of earlier credits (item 36). **Buyer side:** input VAT on unpaid payables deducted (item 55), added back when settled (item 58). **Due** the 25th day after the quarter, with the summary lists of sales and purchases, which every VAT taxpayer files. | NIRC 114 as amended; RR 3-2024; RMC 68-2024; RR 1-2012 | eFPS dates |
| Percentage tax, quarterly (2551Q) | 3% of gross quarterly sales (1% from 1 Jul 2020 to 30 Jun 2023), less tax withheld by government and any advance payments made on Form 0605. Due the 25th day after the quarter. | NIRC 116; CREATE; RMC 49-2025 |: |
| Expanded withholding | Monthly 0619-E for months 1-2 (the 10th of the next month; eFPS groups the 11th-15th); 1601-EQ with the QAP (last day of the month after the quarter); annual 1604-E (1 March, or the next working day). Every withholding return carries its alphalist. | RR 11-2018; RMC 55-2026 | Dates per year |
| VAT on digital services | 1600-VT within 10 days after the month, with its alphalist | RR 3-2025; RMC 55-2026; RMC 59-2026 |: |
| Income tax, corporation | Quarterly 1702Q (60 days after the quarter) and annual 1702-RT (15th day of the 4th month): the higher of 25%/20% regular tax and 2% MCIT, less excess MCIT carried forward, 2307 credits and earlier quarters | NIRC 27, 77 |: |
| Income tax, individual | 1701Q (15 May, 15 Aug, 15 Nov); annual 1701/1701A by 15 April. Micro and small taxpayers may file 1701-MS, on paper or through eBIRForms 7.9.6. Graduated table or 8%. | TRAIN; RMC 20-2026; RMC 37-2026 |: |
| Deduction rules | **OSD** 40%: of gross sales or receipts for individuals, of gross income for corporations. **Entertainment, amusement and recreation** capped at 0.5% of net sales (goods) or 1% of net revenue (services). **Interest expense** reduced by 20% of interest income subjected to final tax. **NOLCO** 3 years (2020-2021 losses: 5 years), shown separately; not available while on OSD, though the 3 years keep running. | NIRC 34 as amended by CREATE; RR 10-2002; RR 25-2020; RR 14-2001 | Arbitrage rate's effective date (CREATE has no retroactive effect); NOLCO under OSD from a secondary source |
| Book-to-tax reconciliation | The differences between book profit and taxable income: EAR over the cap, the interest reduction, income already taxed at source, non-deductible penalties and the income tax itself | NIRC 34 |: |

## E. Books and records
- **Books:** General Journal, General Ledger, Sales, Purchase, Cash Receipts, Cash Disbursements and Inventory, carrying the RR 9-2009 fields.
- **Retention:**
  - Five years from the day after the filing deadline, or from the filing date if late (RA 11976 Sec. 235; RR 7-2024 Secs. 4-5). Records tied to a pending protest or refund claim are kept until it is resolved.
  - Computerized books are kept as electronic copies.
  - The Annex B form a CAS user signs (RMC 5-2021) still says database backups are kept ten years, so keep ten until the RDO says the form follows EOPT.
- **Annual e-books:** due within 30 days after year-end (RMO 9-2021).
- **Audit threshold:** in section A.

## F. Where each part lands in ERPNext (designed in CAS-5b)
- **Tax profile:** Company custom fields and Tax Category.
- **VAT classes:** Item Tax Templates and Sales/Purchase Taxes and Charges Templates, one per class.
- **Expanded withholding:** one Tax Withholding Category per ATC, using ERPNext's dated rates and thresholds, set on the Supplier. The customer's profile drives the "Less: Withholding Tax" line on the sales invoice.
- **2307s received:** a new record linked to the invoice or payment.
- **Reverse-charge VAT:**
  - On digital services: a purchase tax template that books 12% to VAT payable (1600-VT) and to input VAT.
  - On RBE purchases: the same, with input VAT held until the VAT is paid.
- **Senior citizen/PWD:** a discount type with VAT-exempt treatment and the holder's details.
- **Period-end:** reports for each return above, each tested against eBIRForms.

## G. What the eBIRForms package contributed
- **Release notes as an index.** They record every rule change the BIR built into its forms from v6.0 to v7.9.6.2. Each MSME-relevant entry is in this catalogue:
  - TRAIN forms and rates (2018; the 2023 income tax table);
  - CREATE rates and their sunset;
  - 2551M → 2551Q, and 0619-E with 1601-EQ;
  - 2550Q version 2024 and 1701-MS (Aug 2024);
  - 5-digit branch codes;
  - RR 5-2025 platform and credit-card withholding;
  - RA 12023 VAT on digital services;
  - the 0.5% Top Withholding Agent codes;
  - advance payment of percentage tax on Form 0605 (Change Request 3-2024; RMC 49-2025, a payment option rather than a new rule);
  - RR 4-2026, the one-time abatement for micro taxpayers (relief, not an accounting rule).
- **Parked as not MSME-relevant:** excise taxes; DST rate tables (DST on loans, leases and shares to be added later); joint-venture ATCs (RMO 18-2024); offshore gaming; international carriers; treaty codes.
- **One correction to the package:** its notes credit the 0.5% codes (WI840-WC860) to "RR No. 4-2025". The issuance is RR 24-2025 (25 Sep 2025), and RMO 46-2025 created the codes. That's why the issuances, not the package, are the reference of record.
- **Code lists:** the plain XML files weren't needed for this pass. As on 9 Oct, they serve only as a cross-check of ATC membership.
- **Form programs:** the ones inside BIRForms.exe were not decoded.
- **Out of scope until payroll:** compensation withholding, including the de minimis limits from 6 Jan 2026 (RR 29-2025).

## H. Open items for the CPA (RDO where noted)
1. RDO: are non-micro clients using this CAS covered by e-invoicing (RMC 98-2026 Sec. III)?
2. RR 6-2026: what "applicable" covers for the withholding line, and the transition for system-generated invoices.
3. RR 5-2025: confirm from its text that the ₱500,000 threshold and sworn declaration survive.
4. Senior citizen/PWD: the Joint Administrative Order's number; the 20% computation base from the RR/RMC text.
5. NOLCO under OSD, from the primary text.
6. ATC per withholding category; rates and ATCs for tax withheld by government (income tax, percentage tax).
7. Effective date of the 20% interest-arbitrage rate.
8. Sec. 232 audit threshold: the statute text.
9. Mixed-sales input VAT allocation, from the primary text.
10. The reported RR 1-2026 amendment to RR 9-2025 and ATC WV110.
11. Debit notes for invoices that are not e-invoices; the pending sales-adjustment issuance.
12. RDO: retention for the sworn statement. The Annex B form says ten years; EOPT says five.

## Sources
- **Tax rates and regimes:**
  - TRAIN primer (Senate): https://web.senate.gov.ph/publications/STSRO/primer%20on%20TRAIN%20LAW%202018%20as%20of%20march%2013.pdf
  - CREATE (Forvis Mazars): https://www.forvismazars.com/ph/en/insights/tax-alerts/2021-create-act-salient-features
  - CREATE 20% criteria and interest arbitrage (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/lets-talk-tax/how-will-the-create-law-affect-your-2020-itr/
  - CREATE sunset (GMA): https://gmanetwork.com/news/money/economy/874904/covid-19-pandemic-tax-cuts-expire-original-rates-back-bir/story
  - MCIT carry-forward (batasnatin): https://batasnatin.com/laws/tax-MCIT-Sec-27-E-2-percent-1-percent-CREATE
- **Classification and e-invoicing:**
  - RR 8-2024 (PwC): https://pwc.com/ph/en/tax/tax-publications/tax-alerts/2024/tax-alert-20.html
  - RMC 98-2026: https://bir-cdn.bir.gov.ph/BIR/pdf/RMC%20No.%2098-2026%20redacted.pdf
- **Invoicing:**
  - EOPT invoicing (PwC): https://www.pwc.com/ph/en/tax/tax-publications/taxwise-or-otherwise/2024/eopt-invoicing-clarified.html
  - RMC 77-2024 (batasnatin): https://batasnatin.com/laws/rmc-no-77-2024-clarification-on-the-invoicing-requirements-provided-under-rev
  - Buyer information (MTF Counsel): https://mtfcounsel.com/2025/05/08/how-to-comply-with-the-birs-invoicing-requirements/
  - RR 7-2024 Annex B (supplier notice): https://teamenergy.ph/file-manager/files/Notice%20to%20Suppliers_EOPT%20Invoicing%20Requirements.pdf
  - RR 6-2026 (Grant Thornton): https://www.grantthornton.com.ph/technical-alerts/tax-alert/2026/invoices-must-now-disclose-creditable-withholding-tax/
- **EOPT VAT and withholding:**
  - Transitory rules (Forvis Mazars): https://forvismazars.com/ph/en/insights/tax-alerts/ease-of-paying-taxes-act/transitory-provisions-of-eopt-act-issuances
  - Output VAT credit (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/lets-talk-tax/to-give-credit-where-credit-is-due/
  - Withholding and Sec. 34(K) (PwC): https://pwc.com/ph/en/tax/tax-publications/taxwise-or-otherwise/2024/eopt-on-tax-filing-and-withholding-a-closer-look.html
  - Withholding trigger (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/eopt-is-here-revised-rules-on-tax-filing-and-payment-and-matters-affecting-the-declaration-of-taxable-income/
  - Veto of the micro-taxpayer withholding exemption (KPMG): https://assets.kpmg.com/content/dam/kpmg/ph/pdf/InTAX/2024/RA_2024-11976_EoPT_LineVetoMessage.pdf
- **Withholding rates:**
  - RR 11-2018 table (Forvis Mazars): https://www.forvismazars.com/ph/en/insights/tax-alerts/withholding-taxes-in-the-philippines-transactions
  - RR 24-2025 (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/bir-revises-withholding-tax-rates-for-top-withholding-agents/
  - RMO 46-2025 (PwC): https://www.pwc.com/ph/en/tax/tax-publications/tax-alerts/2025/tax-alert-30.html
  - RMC 79-2026 (Context): https://context.ph/2026/07/21/bir-clears-confusion-over-revised-withholding-tax-rules/
- **Platform withholding:**
  - RR 5-2025 (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/amendments-on-certain-income-payments-subject-to-creditable-withholding-tax-under-create-more/
  - RR 5-2025 effectivity (KPMG): https://kpmg.com/ph/en/insights/2025/03/special-intax-march-2025-issue-3-volume-1.html
  - RMO 18-2025 (PwC): https://www.pwc.com/ph/en/tax/tax-publications/tax-alerts/2025/tax-alert-07.html
  - PayMongo merchant guide: https://docs.paymongo.com/docs/account-settings-taxes
- **Government withholding of VAT** (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/how-to-fill-in-vat-returns-from-final-to-creditable-vat-withheld-on-sales-to-govt/
- **VAT on digital services:**
  - PwC Tax Alert 33 (RMC 59-2026): https://www.pwc.com/ph/en/tax/tax-publications/tax-alerts/2026/tax-alert-33.html
  - Grant Thornton: https://www.grantthornton.com.ph/insights/articles-and-updates1/lets-talk-tax/vat-on-digital-services-what-rmc-59-2026-means-for-taxpayers/
  - RR 3-2025 (Aureada): https://www.aureadalaw.com/post/bir-implements-12-vat-on-digital-services-full-guide-to-revenue-regulations-no-3-2025
  - KPMG: https://kpmg.com/ph/en/insights/2025/01/special-intax-january-2025-issue-1-volume-2.html
- **Registered business enterprises:**
  - RR 9-2025 (Grant Thornton): https://www.grantthornton.com.ph/technical-alerts/tax-alert/2025/remittance-of-vat-on-local-sales-of-goods-and-or-services-by-registered-business-enterprises-rbes/
  - RR 10-2025 and RMC 66-2025 (Grant Thornton): https://www.grantthornton.com.ph/technical-alerts/tax-alert/2025/clarifications-on-availing-vat-zero-rating-on-local-purchases-of-rbes/
- **Input VAT:**
  - Capital goods, RMC 21-2022 (PwC): https://www.pwc.com/ph/en/tax/tax-publications/tax-alerts/2022/tax-alert-10.html
  - Mixed sales (batasnatin): https://batasnatin.com/laws/tax-mam-vat-input-allocation-110-mixed-zero-exempt-taxable
- **Interest income:**
  - CMEPA (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/key-highlights-of-capital-markets-efficiency-promotion-act-cmepa/
  - Implementation (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/lets-talk-tax/cmepa-from-law-to-implementation/
- **Senior citizen/PWD:**
  - RR 7-2010 (jur.ph): https://jur.ph/law/summary/implementing-tax-privileges-republic-act-9994-senior-citizens
  - RMC 38-2012 example: https://seniorcitizen.davaocity.gov.ph/index.php/republic-act-9994-page-4
  - PWD 5% (PwC): https://www.pwc.com/ph/en/tax/tax-publications/taxwise-or-otherwise/2019-taxwise-or-otherwise/the-pwd-5-percent-special-discount.html
  - DTI cap increase: https://dti.gov.ph/news/dti-da-doe-increase-senior-citizens-pwd-special-discounts-basic-goods
- **Deductions:**
  - EAR cap (batasnatin): https://batasnatin.com/laws/tax-entertainment-Sec-34-A-1-a-representation-cap
  - NOLCO (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/nolco-from-2020-and-2021-carried-over-for-next-5-years/
  - NOLCO and OSD (CPA Davao, secondary): https://www.cpadavao.com/2015/06/what-is-meant-by-net-operating-loss-carry-over-nolco-in-taxation.html
- **Returns and deadlines:**
  - RMC 20-2026 (batasnatin): https://batasnatin.com/laws/rmc-no-20-2026-guidelines-in-the-filing-of-annual-income-tax-returns-and-paym
  - RMC 37-2026 (PwC): https://www.pwc.com/ph/en/tax/tax-publications/tax-alerts/2026/tax-alert-19.html
  - RMC 49-2025 (batasnatin): https://batasnatin.com/laws/rmc-no-49-2025-availability-of-offline-electronic-bureau-of-internal-revenue
  - Deadlines (JuanTax): https://help.juan.tax/en/articles/310-when-to-file-a-list-of-bir-tax-deadlines
  - RR 1-2012 summary lists (Supreme Court E-Library): https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/10/50215
  - Audit threshold (Grant Thornton TRAIN infographic): https://www.grantthornton.com.ph/globalassets/1.-member-firms/philippines/tax-alerts/2018/01.22.2018/train-infographic_filing-and-compliance-01222018.pdf
- **Retention:** EOPT preservation (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/eopt-is-here-updates-on-the-preservation-of-book-of-accounts-and-changes-in-taxpayer-registration/
- **The package:** Offline eBIRForms Package v7.9.6.2, Release Notes.txt (read statically on 26 Oct 2026)
