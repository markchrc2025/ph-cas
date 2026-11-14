"""validate_map: structural checks on a field map, run every time one is loaded.

A map is data a person edits by hand; a typo here must fail loudly, not print
in the wrong place. Maps are plain dicts (the JSON as loaded); see
docs/reference/birpdf-map-format.md for the format.
"""

import re

from ph_cas.birpdf.errors import BirPdfError

KINDS = ("comb", "money", "mark", "choice", "text", "none")


def _fail(m: dict, what: str):
    raise BirPdfError(f"map {m.get('form')}-{m.get('version')}: {what}")


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_cells(m: dict, key: str, cells, page: int):
    if not isinstance(cells, list) or len(cells) < 2 or not all(_is_num(c) for c in cells):
        _fail(m, f"{key}: cells must be at least two x-boundaries")
    width = m["pages"][page - 1]["width"]
    for i in range(1, len(cells)):
        if not cells[i] > cells[i - 1]:
            _fail(m, f"{key}: cell boundaries must increase ({', '.join(str(c) for c in cells)})")
    if cells[0] < 0 or cells[-1] > width:
        _fail(m, f"{key}: cells run off the page")


def _check_page(m: dict, key: str, page, y) -> int:
    if not isinstance(page, int) or isinstance(page, bool) or page < 1 or page > len(m["pages"]):
        _fail(m, f"{key}: page {page} is not a page of the template")
    if not _is_num(y) or y < 0 or y > m["pages"][page - 1]["height"]:
        _fail(m, f"{key}: y {y} is off the page")
    return page


def _check_field(m: dict, f: dict):
    key = f.get("key")
    if not isinstance(key, str) or key == "":
        _fail(m, "a field has no key")
    kind = f.get("kind")
    if kind == "none":
        reason = f.get("reason")
        if not isinstance(reason, str) or reason.strip() == "":
            _fail(m, f'{key}: kind "none" needs a reason')
        if f.get("expect") is not None:
            re.compile(f["expect"])
        return
    item = f.get("item")
    if not isinstance(item, str) or item == "":
        _fail(m, f"{key}: a placed field needs its item label")
    for c in f.get("blankIf") or []:
        if not isinstance(c.get("key"), str) or not isinstance(c.get("equals"), str):
            _fail(m, f"{key}: blankIf needs key and equals")
    if kind == "comb":
        rows = f.get("rows")
        if not isinstance(rows, list) or not rows:
            _fail(m, f"{key}: a comb needs rows")
        for r in rows:
            _check_cells(m, key, r.get("cells"), _check_page(m, key, r.get("page"), r.get("y")))
        if len(rows) > 1 and f.get("align") == "right":
            _fail(m, f"{key}: right alignment is for one row only")
        if f.get("pad") is not None and len(f["pad"]) != 1:
            _fail(m, f"{key}: pad is one character")
        strip = f.get("strip")
        if strip is not None and (not isinstance(strip, str) or strip == "" or f.get("squeeze") or f.get("date")):
            _fail(m, f"{key}: strip is a non-empty prefix, never with squeeze or date")
        if f.get("squeeze") and (f.get("date") or f.get("pad") or f.get("ghost") == "8" or f.get("align") == "right"):
            _fail(m, f"{key}: squeeze is for letter combs only; digits never squeeze")
        return
    if kind == "money":
        _check_cells(m, key, f.get("cells"), _check_page(m, key, f.get("page"), f.get("y")))
        if f.get("cents"):
            _check_cells(m, key, f["cents"], f["page"])
        return
    if kind == "choice":
        _check_cells(m, key, f.get("cells"), _check_page(m, key, f.get("page"), f.get("y")))
        if not isinstance(f.get("options"), dict):
            _fail(m, f"{key}: a choice needs its options")
        return
    if kind == "mark":
        box = f.get("box") or [None] * 4
        _check_page(m, key, f.get("page"), box[1] if len(box) > 1 else None)
        x0, y0, x1, y1 = box
        if not (x1 > x0 and y1 > y0):
            _fail(m, f"{key}: box must be [x0, y0, x1, y1]")
        return
    if kind == "text":
        _check_page(m, key, f.get("page"), f.get("y"))
        if not (_is_num(f.get("x1")) and _is_num(f.get("x0")) and f["x1"] > f["x0"]):
            _fail(m, f"{key}: x1 must be right of x0")
        if not (_is_num(f.get("minSize")) and f["minSize"] > 0):
            _fail(m, f"{key}: a text field needs minSize")
        if f.get("lines") is not None:
            if not (isinstance(f["lines"], int) and f["lines"] >= 1):
                _fail(m, f"{key}: lines is a whole number of 1 or more")
            if f["lines"] > 1 and not (_is_num(f.get("rowHeight")) and f["rowHeight"] > 0):
                _fail(m, f"{key}: a text field on more than one line needs rowHeight")
            if f["lines"] > 1 and (f.get("align", "left") != "left" or f.get("amount")):
                _fail(m, f"{key}: only left-aligned free text wraps")
        if f.get("amount") and f.get("case") == "keep":
            _fail(m, f"{key}: an amount cell has no case")
        a = f.get("amount")
        if a is not None and a is not True and a is not False and a != "centavos":
            _fail(m, f'{key}: amount is true or "centavos"')
        return
    _fail(m, f'{key}: unknown kind "{kind}"')


def validate_map(m: dict) -> dict:
    if not isinstance(m, dict) or not isinstance(m.get("fields"), list) or not isinstance(m.get("pages"), list) or not m["pages"]:
        raise BirPdfError("field map: missing pages or fields")
    if not (_is_num(m.get("size")) and m["size"] > 0):
        _fail(m, "default size missing")
    for f in m["fields"]:
        _check_field(m, f)
    pp = m.get("printPages")
    if pp is not None:
        ok = (
            isinstance(pp, list)
            and pp
            and all(isinstance(n, int) and 1 <= n <= len(m["pages"]) and (i == 0 or n > pp[i - 1]) for i, n in enumerate(pp))
        )
        if not ok:
            _fail(m, "printPages must list pages of the template in ascending order")
        for f in m["fields"]:
            if f["kind"] == "none":
                continue
            pages = [r["page"] for r in f["rows"]] if f["kind"] == "comb" else [f["page"]]
            for pg in pages:
                if pg not in pp:
                    _fail(m, f"{f['key']}: sits on page {pg}, which is not printed")
    none = {f["key"] for f in m["fields"] if f["kind"] == "none"}
    for f in m["fields"]:
        if f["kind"] != "none" and f["key"] in none:
            _fail(m, f'{f["key"]} is both placed and "none"')
    return m
