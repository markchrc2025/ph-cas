"""layout: the pure heart of the engine. A form map plus the (key, value) rows
of an export become the exact pieces of text to draw (page, x, y, text, size).
No PDF, no files, no clock: the font's metrics come in as a parameter.

Every value either lands inside its boxes or raises a BirPdfError naming the
field. Nothing is ever cut off silently.
"""

import math
import re
from dataclasses import dataclass
from typing import Protocol

from ph_cas.birpdf.errors import BirPdfError


class Metrics(Protocol):
    def width(self, text: str, size: float) -> float: ...

    def cap_height(self, size: float) -> float: ...

    def has(self, ch: str) -> bool: ...


@dataclass(frozen=True)
class DrawOp:
    page: int
    x: float
    y: float
    text: str
    size: float


# The smallest size a squeezed value may print at (domain owner, C1-A1).
SQUEEZE_MIN = 5.5
# Room left at each end of a squeezed line: clears a 1.4 pt page frame by 1.3 pt.
_SQUEEZE_INSET = 2
# Room left at each end of a free-text line or cell.
_TEXT_INSET = 1.5
# Baseline to baseline, as a multiple of the size, for a wrapped free-text field.
_LEADING = 1.15

_AMOUNT = re.compile(r"^(-?)([0-9][0-9,]*)(?:\.([0-9]+))?$")
_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _where(f: dict, m: dict) -> str:
    return f"{m['form']} {m['version']} {f['key']} (item {f['item']})"


def _boxes(row: dict) -> int:
    return len(row["cells"]) - 1


def layout_return(m: dict, rows: list[tuple[str, str]], met: Metrics) -> list[DrawOp]:
    """Lay out every mapped field of an export."""
    values: dict[str, str] = {}
    for k, v in rows:
        if k in values:
            raise BirPdfError(f"{m['form']} {m['version']}: key {k} appears twice in the export", k)
        values[k] = v
    mapped = {f["key"] for f in m["fields"]}
    for k in values:
        if k not in mapped:
            raise BirPdfError(
                f"{m['form']} {m['version']}: key {k} has no entry in the field map (maps/{m['form']}-{m['version']}.json)",
                k,
            )
    ops: list[DrawOp] = []
    for f in m["fields"]:
        v = values.get(f["key"])
        if v is None:
            continue  # the export does not carry this key
        if f["kind"] == "none":
            if f.get("expect") is not None and not re.search(f["expect"], v):
                raise BirPdfError(
                    f"{m['form']} {m['version']} {f['key']}: has no place on the paper ({f['reason']}) but holds \"{v}\"",
                    f["key"],
                )
            continue
        blank_if = f.get("blankIf") or []
        if blank_if and all(values.get(c["key"], "") == c["equals"] for c in blank_if):
            continue
        ops.extend(_place(m, f, v, met))
    return ops


def _place(m: dict, f: dict, v: str, met: Metrics) -> list[DrawOp]:
    size = f.get("size", m["size"])
    kind = f["kind"]
    if kind == "comb":
        return _comb(m, f, v, size, met)
    if kind == "money":
        return _money(m, f, v, size, met)
    if kind == "mark":
        return _mark(m, f, v, size, met)
    if kind == "choice":
        return _choice(m, f, v, size, met)
    return _text(m, f, v, size, met)


def _fill(row: dict, chars: str, start: int, size: float, met: Metrics, who: str) -> list[DrawOp]:
    """Characters centred one per box, starting at box `start`."""
    ops = []
    cells = row["cells"]
    for i, ch in enumerate(chars):
        if ch == " ":
            continue
        if not met.has(ch):
            raise BirPdfError(f'{who}: the character "{ch}" cannot be printed')
        x0, x1 = cells[start + i], cells[start + i + 1]
        ops.append(DrawOp(row["page"], (x0 + x1) / 2 - met.width(ch, size) / 2, row["y"], ch, size))
    return ops


def _date_digits(v: str, who: str) -> str:
    d = _DATE.match(v.strip())
    if not d:
        raise BirPdfError(f'{who}: "{v}" is not a date (MM/DD/YYYY)')
    return d.group(1).rjust(2, "0") + d.group(2).rjust(2, "0") + d.group(3)


def _wrap_words(v: str, widths: list[int]) -> list[str] | None:
    """Break text into rows of the given widths at spaces; a word longer than a row is split."""
    lines = [""]
    for word in [w for w in re.split(r" +", v) if w]:
        w = word
        while True:
            i = len(lines) - 1
            if i >= len(widths):
                return None
            cap = widths[i]
            cur = lines[i]
            joined = f"{cur} {w}" if cur else w
            if len(joined) <= cap:
                lines[i] = joined
                break
            if not cur:
                lines[i] = w[:cap]
                w = w[cap:]
            lines.append("")
    return lines if len(lines) <= len(widths) else None


def _comb(m: dict, f: dict, raw: str, size: float, met: Metrics) -> list[DrawOp]:
    who = _where(f, m)
    v = raw.upper() if f.get("case", "upper") == "upper" else raw
    if v.strip() == "":
        return []
    if f.get("date"):
        v = _date_digits(v, who)
    strip = f.get("strip")
    if strip:
        if not v.startswith(strip):
            raise BirPdfError(f'{who}: "{raw}" does not start with the "{strip}" the paper pre-prints', f["key"])
        v = v[len(strip) :]
    if f.get("drop"):
        v = "".join(c for c in v if c not in f["drop"])
    rows = f["rows"]
    total = sum(_boxes(r) for r in rows)
    if f.get("pad") and len(v) < total:
        v = v.rjust(total, f["pad"])
    if len(v) > total and (f.get("wrap") != "words" or len(rows) == 1):
        if f.get("squeeze"):
            return _squeeze(f, v, raw, size, met, who)
        raise BirPdfError(f'{who}: "{raw}" is {len(v)} characters but the paper has {total} boxes', f["key"])
    if len(rows) == 1:
        row = rows[0]
        start = _boxes(row) - len(v) if f.get("align", "left") == "right" else 0
        return _fill(row, v, start, size, met, who)
    if f.get("wrap") == "words":
        parts = _wrap_words(v, [_boxes(r) for r in rows])
        if parts is None:
            if f.get("squeeze"):
                return _squeeze(f, v, raw, size, met, who)
            raise BirPdfError(
                f'{who}: "{raw}" ({len(v)} characters) does not fit {len(rows)} rows of {" + ".join(str(_boxes(r)) for r in rows)} boxes',
                f["key"],
            )
    else:
        parts = []
        rest = v
        for r in rows:
            parts.append(rest[: _boxes(r)])
            rest = rest[_boxes(r) :]
    ops = []
    for i, r in enumerate(rows):
        ops.extend(_fill(r, parts[i] if i < len(parts) else "", 0, size, met, who))
    return ops


def _wrap_measured(v: str, widths: list[float], size: float, met: Metrics) -> list[str] | None:
    """Break text into lines no wider than each row's width at `size`; None if it overflows."""
    lines = [""]

    def fits(t: str) -> bool:
        return met.width(t, size) <= widths[len(lines) - 1]

    for word in [w for w in re.split(r" +", v) if w]:
        cur = lines[-1]
        joined = f"{cur} {word}" if cur else word
        if fits(joined):
            lines[-1] = joined
            continue
        w = word
        if cur:
            lines.append("")
        while True:
            if len(lines) > len(widths):
                return None
            if fits(w):
                lines[-1] = w
                break
            n = len(w) - 1
            while n > 0 and not fits(w[:n]):
                n -= 1
            if n == 0:
                return None
            lines[-1] = w[:n]
            w = w[n:]
            lines.append("")
    return lines if len(lines) <= len(widths) else None


def _squeeze(f: dict, v: str, raw: str, size: float, met: Metrics, who: str) -> list[DrawOp]:
    """A value too long for its boxes, printed whole: one continuous line per row
    across the comb's full width, at the largest size from `size` down to
    SQUEEZE_MIN that fits, vertically centred on the same middle line as the
    one-per-box characters. Below SQUEEZE_MIN it is an error naming the field."""
    for ch in v:
        if ch != " " and not met.has(ch):
            raise BirPdfError(f'{who}: the character "{ch}" cannot be printed', f["key"])
    rows = f["rows"]
    widths = [r["cells"][-1] - r["cells"][0] - 2 * _SQUEEZE_INSET for r in rows]
    tenths = round(size * 10)
    while tenths >= SQUEEZE_MIN * 10:
        s = tenths / 10
        lines = _wrap_measured(v, widths, s, met)
        if lines is not None:
            lift = (met.cap_height(size) - met.cap_height(s)) / 2
            return [
                DrawOp(r["page"], r["cells"][0] + _SQUEEZE_INSET, r["y"] + lift, lines[i], s)
                for i, r in enumerate(rows)
                if i < len(lines) and lines[i]
            ]
        tenths -= 1
    raise BirPdfError(
        f'{who}: "{raw}" ({len(v)} characters) does not fit the comb even squeezed to {SQUEEZE_MIN} pt', f["key"]
    )


def _money(m: dict, f: dict, raw: str, size: float, met: Metrics) -> list[DrawOp]:
    who = _where(f, m)
    v = raw.strip()
    if v == "":
        return []
    a = _AMOUNT.match(v)
    if not a:
        raise BirPdfError(f'{who}: "{raw}" is not an amount', f["key"])
    pesos = a.group(1) + a.group(2).replace(",", "")
    centavos = a.group(3) or ""
    row = {"page": f["page"], "y": f["y"], "cells": f["cells"]}
    n = _boxes(row)
    if len(pesos) > n:
        raise BirPdfError(f'{who}: "{raw}" needs {len(pesos)} boxes before the point but the paper has {n}', f["key"])
    ops = _fill(row, pesos, n - len(pesos), size, met, who)
    if not f.get("cents"):
        if re.search(r"[1-9]", centavos):
            raise BirPdfError(f'{who}: "{raw}" has centavos but the paper has no centavo boxes', f["key"])
        return ops
    cents = {"page": f["page"], "y": f["y"], "cells": f["cents"]}
    nc = _boxes(cents)
    c = centavos.ljust(nc, "0")
    if len(c) > nc and re.search(r"[1-9]", c[nc:]):
        raise BirPdfError(f'{who}: "{raw}" has {len(c)} decimals but the paper has {nc} centavo boxes', f["key"])
    return ops + _fill(cents, c[:nc], 0, size, met, who)


def _mark_at(f: dict, size: float, met: Metrics) -> DrawOp:
    x0, y0, x1, y1 = f["box"]
    return DrawOp(f["page"], (x0 + x1) / 2 - met.width("X", size) / 2, (y0 + y1) / 2 - met.cap_height(size) / 2, "X", size)


def _mark(m: dict, f: dict, v: str, size: float, met: Metrics) -> list[DrawOp]:
    if v not in ("true", "false"):
        raise BirPdfError(f'{_where(f, m)}: a checkbox takes "true" or "false", not "{v}"', f["key"])
    return [_mark_at(f, size, met)] if v == f.get("when", "true") else []


def _choice(m: dict, f: dict, v: str, size: float, met: Metrics) -> list[DrawOp]:
    label = f["options"].get(v)
    if label is None:
        raise BirPdfError(f'{_where(f, m)}: "{v}" is not one of the dropdown\'s options', f["key"])
    row = {"page": f["page"], "y": f["y"], "cells": f["cells"]}
    n = _boxes(row)
    if len(label) > n:
        raise BirPdfError(f'{_where(f, m)}: "{label}" is {len(label)} characters but the paper has {n} boxes', f["key"])
    start = n - len(label) if f.get("align", "left") == "right" else 0
    return _fill(row, label, start, size, met, _where(f, m))


def _centavo_amount(v: str, raw: str, who: str, key: str) -> str:
    """Pesos and centavos as typed: thousands separators and exactly two decimals.
    "1234.5" prints "1,234.50". Never rounded: a third non-zero decimal is an error."""
    a = _AMOUNT.match(re.sub(r"^(-?)\.", r"\g<1>0.", v))
    if not a:
        raise BirPdfError(f'{who}: "{raw}" is not an amount', key)
    dec = a.group(3) or ""
    if re.search(r"[1-9]", dec[2:]):
        raise BirPdfError(f'{who}: "{raw}" has more than two decimals; the paper has pesos and centavos only', key)
    pesos = re.sub(r"^0+(?=\d)", "", a.group(2).replace(",", ""))
    grouped = f"{int(pesos):,}"
    return f"{a.group(1)}{grouped}.{dec.ljust(2, '0')[:2]}"


def _text_lines(f: dict, v: str, room: float, size: float, met: Metrics) -> tuple[float, list[DrawOp]] | None:
    """A free-text value broken over up to f["lines"] lines inside its row.

    The largest size from `size` down to minSize at which every line fits the
    width and the block fits f["rowHeight"] (the clear height between the
    row's rules). The block is centred on the middle of the single line it
    replaces. None when even minSize does not fit."""
    n = int(f["lines"])
    height = float(f["rowHeight"])
    tenths = round(size * 10)
    while tenths >= round(f["minSize"] * 10):
        s = tenths / 10
        lead = s * _LEADING
        if (n - 1) * lead + met.cap_height(s) <= height:
            lines = _wrap_measured(v, [room] * n, s, met)
            if lines is not None:
                lines = [ln for ln in lines if ln]
                k = len(lines)
                # middle of the block = middle of the single line at `size`
                top = f["y"] + met.cap_height(size) / 2 - met.cap_height(s) / 2 + (k - 1) * lead / 2
                x = f["x0"] + _TEXT_INSET
                return s, [DrawOp(f["page"], x, top - i * lead, ln, s) for i, ln in enumerate(lines)]
        tenths -= 1
    return None


def _text(m: dict, f: dict, raw: str, size: float, met: Metrics) -> list[DrawOp]:
    who = _where(f, m)
    v = (raw.upper() if f.get("case", "upper") == "upper" else raw).strip()
    if v == "":
        return []
    amount = f.get("amount")
    if amount == "centavos":
        v = _centavo_amount(v, raw, who, f["key"])
    elif amount:
        a = _AMOUNT.match(v)
        if not a:
            raise BirPdfError(f'{who}: "{raw}" is not an amount', f["key"])
        if re.search(r"[1-9]", a.group(3) or ""):
            raise BirPdfError(f'{who}: "{raw}" has centavos but the paper asks for whole pesos', f["key"])
        v = a.group(1) + a.group(2).replace(",", "")
    for ch in v:
        if ch != " " and not met.has(ch):
            raise BirPdfError(f'{who}: the character "{ch}" cannot be printed', f["key"])
    room = f["x1"] - f["x0"] - 2 * _TEXT_INSET
    s = size
    w = met.width(v, size)
    if w > room:
        s = math.floor((size * room / w) * 10) / 10
        wrapped = _text_lines(f, v, room, size, met) if int(f.get("lines") or 1) > 1 else None
        if wrapped is not None and wrapped[0] > s:
            return wrapped[1]
        if s < f["minSize"]:
            raise BirPdfError(
                f'{who}: "{raw}" is {len(v)} characters; it needs {w * f["minSize"] / size:.1f} pt at the minimum {f["minSize"]} pt size but the line is {room:.1f} pt',
                f["key"],
            )
    tw = met.width(v, s)
    align = f.get("align", "left")
    if align == "left":
        x = f["x0"] + _TEXT_INSET
    elif align == "right":
        x = f["x1"] - _TEXT_INSET - tw
    else:
        x = (f["x0"] + f["x1"]) / 2 - tw / 2
    return [DrawOp(f["page"], x, f["y"], v, s)]


def layout_ghost(m: dict, met: Metrics) -> list[DrawOp]:
    """The proof layout: a ghost value in every placed field, every box filled.
    8 in digit boxes, W in letter boxes, X in every checkbox, and the item
    number on every free-text line. Conditions (blankIf) are ignored."""
    ops: list[DrawOp] = []
    seen_box: set[str] = set()
    for f in m["fields"]:
        kind = f["kind"]
        if kind == "none":
            continue
        size = f.get("size", m["size"])
        who = _where(f, m)
        if kind == "comb":
            for r in f["rows"]:
                ops.extend(_fill(r, f.get("ghost", "W") * _boxes(r), 0, size, met, who))
        elif kind == "choice":
            r = {"page": f["page"], "y": f["y"], "cells": f["cells"]}
            ops.extend(_fill(r, "W" * _boxes(r), 0, size, met, who))
        elif kind == "money":
            r = {"page": f["page"], "y": f["y"], "cells": f["cells"]}
            ops.extend(_fill(r, "8" * _boxes(r), 0, size, met, who))
            if f.get("cents"):
                c = {"page": f["page"], "y": f["y"], "cells": f["cents"]}
                ops.extend(_fill(c, "8" * _boxes(c), 0, size, met, who))
        elif kind == "mark":
            ident = f"{f['page']}:{','.join(str(b) for b in f['box'])}"
            if ident not in seen_box:
                ops.append(_mark_at(f, size, met))
            seen_box.add(ident)
        elif kind == "text":
            ops.extend(_text(m, {**f, "case": "keep", "amount": False}, f["item"], size, met))
    return ops
