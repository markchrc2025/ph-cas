from frappe.model.document import Document


class PHModules(Document):
    def on_update(self):
        from ph_cas.modules.api import after_change

        after_change(self)
        from ph_cas.home.progress import mark_modules_chosen

        mark_modules_chosen()  # B91: the checklist's 'Choose what you use'
