from frappe.model.document import Document


class PHApprovalChain(Document):
    def __setup__(self):
        # Blank company means every company. Frappe would otherwise fill a blank company
        # with the saving user's default company on insert, so a chain meant for every
        # company silently applied to one.
        self.dont_update_if_missing = ["company"]
