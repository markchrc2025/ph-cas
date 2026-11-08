"""B08: exports carry the Annex B header as their first lines.

ph_cas reports export through these helpers rather than the report view's
generic Export, so every CSV and Excel file a client hands over opens with
the taxpayer's name, TIN-branch, software and version, user and time.
"""

import csv
import io

import frappe

from ph_cas.audit.header import ph_header_lines


def csv_with_header(columns: list[str], rows: list[list], company: str | None = None) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    for line in ph_header_lines(company):
        w.writerow([line])
    w.writerow([])
    w.writerow(columns)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return out.getvalue().encode("utf-8-sig")


def xlsx_with_header(columns: list[str], rows: list[list], company: str | None = None, sheet: str = "Report") -> bytes:
    from frappe.utils.xlsxutils import make_xlsx

    data = [[line] for line in ph_header_lines(company)] + [[]] + [columns] + [["" if v is None else v for v in r] for r in rows]
    return make_xlsx(data, sheet).getvalue()


@frappe.whitelist()
def download_report(report_name: str, filters: str | None = None, file_format: str = "CSV"):
    """Download any ph_cas script report with the header lines."""
    import json

    from frappe.desk.query_report import run

    filters = json.loads(filters) if isinstance(filters, str) else (filters or {})
    frappe.has_permission("Report", "read", report_name, throw=True)
    result = run(report_name, filters=filters, ignore_prepared_report=True)
    cols = result.get("columns") or []
    labels = [c.get("label") if isinstance(c, dict) else str(c).split(":")[0] for c in cols]
    keys = [c.get("fieldname") if isinstance(c, dict) else None for c in cols]
    rows = []
    for r in result.get("result") or []:
        if isinstance(r, dict):
            rows.append([r.get(k) for k in keys])
        else:
            rows.append(list(r))
    company = filters.get("company")
    if file_format.upper() == "XLSX":
        content = xlsx_with_header(labels, rows, company, sheet=report_name[:30])
        frappe.response["type"] = "binary"
        frappe.response["filename"] = f"{report_name}.xlsx"
    else:
        content = csv_with_header(labels, rows, company)
        frappe.response["type"] = "binary"
        frappe.response["filename"] = f"{report_name}.csv"
    frappe.response["filecontent"] = content
    from ph_cas.audit.events import record

    record("export", "Report", report_name, 0, {"format": file_format, "filters": filters})
