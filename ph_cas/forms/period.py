"""Taxable periods. A period key is "2026-03" (a month), "2026-Q1" (a quarter)
or "2026" (a year). For a fiscal-year client the year is the calendar year in
which the fiscal year ends, and quarter n is the nth quarter of that fiscal
year: with a fiscal year starting in July, "2026-Q1" is July to September 2025.
Withholding returns and the 2551Q follow the calendar whatever the fiscal year.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date

MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
QUARTER = re.compile(r"^(\d{4})-Q([1-4])$", re.I)
YEAR = re.compile(r"^(\d{4})$")


@dataclass(frozen=True)
class Period:
    key: str
    kind: str  # month, quarter, year
    year: int
    n: int  # month 1 to 12, quarter 1 to 4, or 0 for a year
    start: date
    end: date
    fiscal: bool = False

    @property
    def label(self) -> str:
        if self.kind == "month":
            return f"{calendar.month_name[self.n]} {self.year}"
        if self.kind == "quarter":
            return f"Q{self.n} {self.year}" + (" (fiscal)" if self.fiscal else "")
        return f"{self.year}" + (" (fiscal)" if self.fiscal else "")

    @property
    def quarter_no(self) -> int:
        return self.n if self.kind == "quarter" else (self.start.month - 1) // 3 + 1


def last_day(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def fiscal_start_month(fiscal_year_start) -> int:
    """The month a fiscal year starts in, 1 for a calendar year. Accepts a date or
    "yyyy-mm-dd"; anything else is calendar."""
    if not fiscal_year_start:
        return 1
    m = fiscal_year_start.month if isinstance(fiscal_year_start, date) else int(str(fiscal_year_start)[5:7] or 1)
    return m if 1 <= m <= 12 else 1


def quarter_range(year: int, q: int, start_month: int = 1) -> tuple[date, date]:
    """Quarter q of the year named `year`. A fiscal year that starts after January is
    named by the year it ends in, so it began the year before."""
    m0 = start_month + 3 * (q - 1)
    y0 = year if start_month == 1 else year - 1
    if m0 > 12:
        m0 -= 12
        y0 += 1
    m1, y1 = m0 + 2, y0
    if m1 > 12:
        m1 -= 12
        y1 += 1
    return date(y0, m0, 1), last_day(y1, m1)


def year_range(year: int, start_month: int = 1) -> tuple[date, date]:
    if start_month == 1:
        return date(year, 1, 1), date(year, 12, 31)
    return date(year - 1, start_month, 1), last_day(year, start_month - 1)


def parse(key: str, kind: str, fiscal_year_start=None) -> Period:
    """A Period from its key, checked against the form's period kind."""
    key = (key or "").strip().upper()
    sm = fiscal_start_month(fiscal_year_start)
    if kind == "month":
        m = MONTH.match(key)
        if not m:
            raise ValueError(f'"{key}" is not a month (yyyy-mm)')
        y, mo = int(m.group(1)), int(m.group(2))
        return Period(key, "month", y, mo, date(y, mo, 1), last_day(y, mo))
    if kind == "quarter":
        m = QUARTER.match(key)
        if not m:
            raise ValueError(f'"{key}" is not a quarter (yyyy-Qn)')
        y, q = int(m.group(1)), int(m.group(2))
        s, e = quarter_range(y, q, sm)
        return Period(f"{y}-Q{q}", "quarter", y, q, s, e, sm != 1)
    m = YEAR.match(key)
    if not m:
        raise ValueError(f'"{key}" is not a year (yyyy)')
    y = int(m.group(1))
    s, e = year_range(y, sm)
    return Period(key, "year", y, 0, s, e, sm != 1)


def key_for(kind: str, start: date, fiscal_year_start=None) -> str:
    """The period key of the period that starts on `start`."""
    sm = fiscal_start_month(fiscal_year_start)
    if kind == "month":
        return f"{start.year}-{start.month:02d}"
    if kind == "quarter":
        offset = (start.month - sm) % 12
        q = offset // 3 + 1
        year = start.year if sm == 1 else (start.year + 1 if start.month >= sm else start.year)
        return f"{year}-Q{q}"
    year = start.year if sm == 1 else start.year + 1
    return str(year)


def mdy(d: date, pad_month: bool = False) -> str:
    """"1/01/2026" (eBIRForms quarter ranges: month not padded, day padded) or "01/01/2026"."""
    return f"{d.month:02d}/{d.day:02d}/{d.year}" if pad_month else f"{d.month}/{d.day:02d}/{d.year}"
