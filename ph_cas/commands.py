import click
import frappe
from frappe.commands import get_site, pass_context


@click.command("ph-cas-sign-off")
@click.argument("path")
@pass_context
def sign_off(context, path):
    """Flip the rules listed in a CPA sign-off file to confirmed."""
    site = get_site(context)
    frappe.init(site=site)
    frappe.connect()
    try:
        from ph_cas.tax.rules import apply_signoff

        out = apply_signoff(path)
        frappe.db.commit()
        click.echo(f"confirmed: {len(out['confirmed'])} missing: {out['missing']}")
    finally:
        frappe.destroy()


commands = [sign_off]
