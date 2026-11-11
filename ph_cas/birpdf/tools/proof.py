"""Write the proof prints of a map: a ghost value in every mapped field, the
form's sample fixture as a DRAFT preview, and the sample with every squeeze
field given a value too long for its boxes.

    bench --site <site> execute ph_cas.birpdf.tools.proof.write --args "['2551Q']"
    (or: python -m ph_cas.birpdf.tools.proof 2551Q [out_dir])

Rasterize every page (pdftoppm -r 300) and check that every character sits
inside its box, centred, and covers no printed text. Proofs are not committed
(they are 1 to 4 MB each); the maps and the fixtures are.
"""

import json
import os
import sys
from datetime import datetime

from ph_cas.birpdf import load_map, parse_ebir_export, render_proof, render_return

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONS = {
    "0619E": "2018-01",
    "1601C": "2018-01",
    "1601EQ": "2019-01",
    "1701": "2018-01",
    "1701A": "2018-01",
    "1701Q": "2018-01",
    "1702Q": "2018-01",
    "1702RT": "2018-01",
    "2307": "2018-01",
    "2550Q": "2024-04",
    "2551Q": "2018-01",
}
LONG = "A VERY LONG INVENTED NAME THAT RUNS PAST EVERY BOX OF THE COMB ON THE BIR BLANK FORM INC"
FIXED_TIME = datetime(2026, 1, 15, 14, 5)


def _long_for(field: dict) -> str:
    boxes = sum(len(r["cells"]) - 1 for r in field["rows"])
    words = (LONG + " ") * 4
    return words[: max(boxes * 3, 12)].rstrip()


def sample_rows(form: str) -> list[tuple[str, str]] | None:
    for name in (f"{form}-sample.xml", f"{form}-sample.json"):
        path = os.path.join(ROOT, "fixtures", name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            return parse_ebir_export(text) if name.endswith(".xml") else [tuple(r) for r in json.loads(text)]
    return None


def write(form: str, out_dir: str | None = None) -> list[str]:
    version = VERSIONS[form]
    out_dir = out_dir or os.path.join(ROOT, "proofs")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    base = os.path.join(out_dir, f"{form}-{version}")
    with open(f"{base}-proof.pdf", "wb") as fh:
        fh.write(render_proof(form, version))
    written.append(f"{base}-proof.pdf")
    rows = sample_rows(form)
    if rows:
        with open(f"{base}-draft-proof.pdf", "wb") as fh:
            fh.write(render_return(form, version, rows, "DRAFT", FIXED_TIME))
        written.append(f"{base}-draft-proof.pdf")
        m = load_map(form, version)
        squeeze = {f["key"]: f for f in m["fields"] if f.get("squeeze")}
        if squeeze:
            # the longest value each comb takes at 5.5 pt: about three characters per box
            long_rows = [(k, _long_for(squeeze[k]) if k in squeeze else v) for k, v in rows]
            with open(f"{base}-longname-proof.pdf", "wb") as fh:
                fh.write(render_return(form, version, long_rows))
            written.append(f"{base}-longname-proof.pdf")
    return written


if __name__ == "__main__":
    forms = [sys.argv[1]] if len(sys.argv) > 1 and sys.argv[1] in VERSIONS else list(VERSIONS)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    for f in forms:
        for p in write(f, out):
            print(p)
