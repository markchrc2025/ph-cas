from frappe.model.document import Document


class PHModules(Document):
    def on_update(self):
        from ph_cas.modules.api import after_change

        after_change(self)
