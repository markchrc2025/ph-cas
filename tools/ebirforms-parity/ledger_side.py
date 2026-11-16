# Runs the Ledger engine for /tmp/ebirpar/scen.json and writes /tmp/ebirpar/ledger.json
import json
from ph_cas.forms.engine import Context
from ph_cas.forms.period import parse as parse_period
from ph_cas.forms.registry import spec
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_f1_2551q import TAXPAYER
from ph_cas.tests.test_g3_income_tax import INDIVIDUAL
import importlib
sc = json.load(open('/tmp/ebirpar/scen.json'))
s = spec(sc['form'])
base = INDIVIDUAL if sc.get('taxpayer') == 'individual' else TAXPAYER
c = dict(base, name=TEST_COMPANY, company_name=TEST_COMPANY, **sc.get('company', {}))
ctx = Context(s, parse_period(sc["period"], s.period), c, contact_number="09170000000", return_name="T", is_amended=bool(sc.get("amended")))
mod = importlib.import_module('ph_cas.forms.f' + s.key.lower().replace('-', ''))
comp = mod.compute(sc['data'], ctx)
out = {'comp': {str(l['item']): str(l['amount']) for l in comp if l['item'] != '_o'}}
if hasattr(mod, 'export_rows'):
    rows, _n = mod.export_rows(sc['data'], comp, ctx)
    out['export'] = {k.split(':', 1)[-1]: v for k, v in rows}
if sc.get('map'):
    from ph_cas.forms.money import amt
    out['export'] = {eid: amt(out['comp'][item]) for eid, item in sc['map'].items()}
json.dump(out, open('/tmp/ebirpar/ledger.json', 'w'), indent=1)
print('ok', len(out.get('export', {})), 'export keys')
