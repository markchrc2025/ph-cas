"""The BIR form engine: what turns the books' figures into a return.

Three kinds of figure sit on every return (docs/plans/bir-tax-forms-build-plan.md):
  books    a sum over posted records for the period, with its record count and a
           filter that opens them; kept in the draft's data with a `_source`
  typed    the user's: penalties, prior-period credits, choices
  derived  the compute: totals, tax due, carry-overs; never stored, always recomputed

Per form, `ph_cas/forms/<code>/` holds compute.py (data in, every item out),
export.py or print_rows.py (the key list the eBIRForms file or the blank's
overlay takes) and feed.py (the books feed). The registry says which forms
exist and how each behaves; money, period, needs and export are shared.
"""
