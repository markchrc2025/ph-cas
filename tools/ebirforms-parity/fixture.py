# python3 fixture.py <form> <scenario.json> <ebir.json> : writes the repo fixture
import json, re, sys
form, scen, ebir = sys.argv[1:4]
s = json.load(open(scen)); e = json.load(open(ebir))
SKIP = re.compile(r"TIN|ZIP|Zip|RDO|Branch|Year|Month|Pages|Contact|Tel|BirthDate|txtSheets")
amounts = {k: v for k, v in e.items() if v is not None and not SKIP.search(k) and re.fullmatch(r"\(?-?[\d,]*\d(\.\d\d)?\)?", v or "")}
s["ebirforms"] = amounts
s["source"] = "Computed by eBIRForms v7.9.6.2 itself (the form " + s.pop("ebir_form", "") + " unpacked by BIRForms.exe), with these inputs typed in, on " + __import__("datetime").date.today().strftime("%d %b %Y")
import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ph_cas", "tests", "data", "ebirforms_parity", f"{form}.json")
json.dump(s, open(out, "w"), indent=1); print(out, len(amounts), "figures")
# optional: <deviations.json> {key: reason}: where eBIRForms' own code breaks, keep its figure on record and expect Ledger's
if len(sys.argv) > 4:
    dev = json.load(open(sys.argv[4]))
    led = json.load(open(sys.argv[3].replace('.ebir.json', '.json')))['export']
    s["ebirforms_defects"] = {k: {"ebirforms": e.get(k), "ledger": led.get(k), "why": why} for k, why in dev.items()}
    for k in dev:
        s["ebirforms"][k] = led.get(k)
    json.dump(s, open(out, "w"), indent=1); print("with", len(dev), "recorded eBIRForms defects")
