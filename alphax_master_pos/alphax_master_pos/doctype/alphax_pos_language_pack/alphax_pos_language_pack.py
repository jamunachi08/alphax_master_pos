import frappe, json
from frappe.model.document import Document

class AlphaXPOSLanguagePack(Document):
    def validate(self):
        if self.translations_json:
            try:
                json.loads(self.translations_json)
            except Exception:
                frappe.throw("Translations JSON is invalid.")
