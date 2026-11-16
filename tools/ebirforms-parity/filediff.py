# python3 filediff.py <ledger.json> <saved.json> <ns> : the Ledger file against the file eBIRForms saves
import json, sys, urllib.parse as u
led = json.load(open(sys.argv[1]))["export"]; saved = json.load(open(sys.argv[2])); ns = sys.argv[3]
lk = {(k if k.startswith(("txt", "result", "ebir", "drive")) and ":" not in k and not k.startswith("Sched") and ns + k not in [x for x, _ in saved] else ns + k): v for k, v in led.items()}
sk = [k for k, _ in saved]; sv = dict(saved)
print("only in eBIRForms:", [k for k in sk if k not in lk])
print("only in Ledger:", [k for k in lk if k not in sv])
num = lambda v: u.unquote(v).replace(",", "")
diff = [(k, lk[k], u.unquote(sv[k])) for k in sk if k in lk and num(lk[k]) != num(sv[k])]
print("values differ:", diff)
