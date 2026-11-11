"""The BIR's "Tax Return Receipt Confirmation" e-mail: what ties a filing to the
BIR. Reads only what the checks need (the sender, the title, the sentence, the
file name, the date and time the BIR received the return) from the text of an
.eml, a .pdf print of the mail, or a .txt. Pure: no database.

The file name shapes were verified from real e-mails (invented TINs here):
  2550Q   111222333000-2550Qv2024-122026Q1.xml
  1701Q   111222333000-1701Qv2018-2025Q3.xml
  1601EQ  11122233300000-1601EQ-2026Q3.xml
  0619E   11122233300000-0619E-072026.xml
The rest follow the eBIRForms file names the Ledger itself writes (dashes optional).
An amended return carries a V suffix (V1, V2) before .xml.
"""

import email
import email.policy
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

BIR_SENDER = "ebirforms-noreply@bir.gov.ph"
BIR_TITLE = "Tax Return Receipt Confirmation"
BIR_SENTENCE = "This confirms receipt of your submission"
MANILA = ZoneInfo("Asia/Manila")

_DATE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})\b")
_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\s*([AaPp])\.?[Mm]\.?")
_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

_TB = r"(\d{9})(\d{3}|\d{5})"
_D = r"-?"
_AMEND = r"(?:V(\d+))?"


def _rx(body: str):
    return re.compile(rf"^{_TB}{_D}{body}{_AMEND}\.xml$", re.I)


@dataclass
class ParsedFileName:
    file_name: str
    tin: str
    branch: int
    form: str  # compact key: 2550Q, 1601EQ, 0619E ...
    version: str | None
    fy_end_month: int | None
    tax_year: int
    quarter: int | None
    month: int | None
    amendment: int | None


# (form key, pattern, reader of the groups after TIN and branch)
_SHAPES = [
    ("2550Q", _rx(rf"2550Q{_D}v(\d{{4}}){_D}(\d{{2}})(\d{{4}})Q([1-4])"), lambda g: (g[2], int(g[3]), int(g[4]), int(g[5]), None, g[6])),
    ("1701Q", _rx(rf"1701Q{_D}v(\d{{4}}){_D}(\d{{4}})Q([1-4])"), lambda g: (g[2], None, int(g[3]), int(g[4]), None, g[5])),
    ("1601EQ", _rx(rf"1601EQ{_D}(\d{{4}})Q([1-4])"), lambda g: (None, None, int(g[2]), int(g[3]), None, g[4])),
    ("0619E", _rx(rf"0619E{_D}(\d{{2}})(\d{{4}})"), lambda g: (None, None, int(g[3]), None, int(g[2]), g[4])),
    ("1600VT", _rx(rf"1600VT{_D}(\d{{2}})(\d{{4}})"), lambda g: (None, None, int(g[3]), None, int(g[2]), g[4])),
    ("2551Q", _rx(rf"2551Q{_D}v(\d{{4}}){_D}(\d{{2}})(\d{{4}})Q([1-4])"), lambda g: (g[2], int(g[3]), int(g[4]), int(g[5]), None, g[6])),
    ("1701", _rx(rf"1701{_D}v(\d{{4}}){_D}(\d{{2}})(\d{{4}})"), lambda g: (g[2], int(g[3]), int(g[4]), None, None, g[5])),
    ("1701A", _rx(rf"1701A{_D}(\d{{2}})(\d{{4}})"), lambda g: (None, int(g[2]), int(g[3]), None, None, g[4])),
    ("1702Q", _rx(rf"1702Q{_D}(\d{{4}})Q([1-4])"), lambda g: (None, None, int(g[2]), int(g[3]), None, g[4])),
    ("1702RT", _rx(rf"1702RT{_D}v(\d{{4}}){_D}(\d{{2}})(\d{{4}})"), lambda g: (g[2], int(g[3]), int(g[4]), None, None, g[5])),
]


def parse_file_name(name: str) -> ParsedFileName | None:
    name = (name or "").strip()
    for form, rx, read in _SHAPES:
        m = rx.match(name)
        if not m:
            continue
        g = m.groups()
        version, fy_end, year, quarter, month, amend = read(g)
        return ParsedFileName(name, g[0], int(g[1]), form, version, fy_end, year, quarter, month, int(amend) if amend else None)
    return None


@dataclass
class ConfirmationFacts:
    from_bir: bool
    file_name: str | None
    received_at: datetime | None  # Manila time
    sha256: str


def _after(text: str, label: str, span: int) -> str | None:
    m = re.search(label, text, re.I)
    if not m:
        return None
    return text[m.end() : m.end() + span]


def _month_number(word: str) -> int | None:
    w = word.lower()
    for i, name in enumerate(_MONTHS):
        if name == w or (3 <= len(w) <= 4 and name.startswith(w)):
            return i + 1
    return None


def parse_received(date_text: str, time_text: str) -> datetime | None:
    d = _DATE.search(date_text or "")
    t = _TIME.search(time_text or "")
    if not d or not t:
        return None
    month = _month_number(d.group(2))
    hour, minute = int(t.group(1)), int(t.group(2))
    if month is None or hour < 1 or hour > 12 or minute > 59:
        return None
    hour = hour % 12 + (12 if t.group(3).lower() == "p" else 0)
    try:
        return datetime(int(d.group(3)), month, int(d.group(1)), hour, minute, tzinfo=MANILA)
    except ValueError:
        return None


def text_of(content: bytes, filename: str) -> str:
    """The readable text of an .eml (headers and body), a .pdf (its text) or a .txt."""
    lower = (filename or "").lower()
    if lower.endswith(".pdf"):
        import io

        from pypdf import PdfReader

        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
    if lower.endswith(".eml") or content[:5] in (b"From:", b"Recei", b"Retur", b"Deliv") or b"\nSubject:" in content[:4000]:
        msg = email.message_from_bytes(content, policy=email.policy.default)
        parts = [f"From: {msg.get('From', '')}", f"Subject: {msg.get('Subject', '')}"]
        body = msg.get_body(preferencelist=("plain", "html"))
        if body is not None:
            text = body.get_content()
            if body.get_content_type() == "text/html":
                text = re.sub(r"<[^>]+>", " ", text)
            parts.append(text)
        return "\n".join(parts)
    return content.decode("utf-8", errors="replace")


def read_confirmation(content: bytes, filename: str) -> ConfirmationFacts:
    text = text_of(content, filename)
    lower = text.lower()
    from_bir = BIR_SENDER in lower and BIR_TITLE.lower() in lower and BIR_SENTENCE.lower() in lower
    file_name = None
    window = _after(text, r"File\s+name\s*:", 200)
    if window is not None:
        glued = re.sub(r"\s+", "", window)
        m = re.match(r"^[^\s]*?\.xml", glued, re.I)
        file_name = m.group(0) if m else None
    date_w = _after(text, r"Date\s+received\s+by\s+BIR\s*:", 60) or ""
    time_w = _after(text, r"Time\s+received\s+by\s+BIR\s*:", 40) or ""
    return ConfirmationFacts(from_bir, file_name, parse_received(date_w, time_w), hashlib.sha256(content).hexdigest())


def check_against(facts: ConfirmationFacts, form_key: str, tin: str, branch: str, period_kind: str, year: int, n: int) -> list[str]:
    """The errors that block marking filed; empty when the confirmation matches the return."""
    errors = []
    if not facts.from_bir:
        errors.append("This is not the BIR's Tax Return Receipt Confirmation e-mail (sender, title or sentence missing).")
    if not facts.file_name:
        errors.append("The confirmation names no .xml file.")
        return errors
    p = parse_file_name(facts.file_name)
    if not p:
        errors.append(f"The file name {facts.file_name} is not one the BIR writes for a return.")
        return errors
    if p.form != form_key:
        errors.append(f"The confirmation is for a {p.form}, not this {form_key}.")
    if p.tin != re.sub(r"\D", "", tin or ""):
        errors.append("The TIN in the confirmation is not this company's.")
    if p.branch != int(re.sub(r"\D", "", branch or "0") or 0):
        errors.append("The branch code in the confirmation is not this company's.")
    if p.tax_year != year:
        errors.append(f"The confirmation is for {p.tax_year}, not {year}.")
    if period_kind == "quarter" and p.quarter != n:
        errors.append(f"The confirmation is for quarter {p.quarter}, not quarter {n}.")
    if period_kind == "month" and p.month != n:
        errors.append(f"The confirmation is for month {p.month}, not month {n}.")
    if facts.received_at is None:
        errors.append("The confirmation does not say when the BIR received the return.")
    return errors
