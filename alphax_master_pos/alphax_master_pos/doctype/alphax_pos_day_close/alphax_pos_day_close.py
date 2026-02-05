import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class AlphaXPOSDayClose(Document):
    def before_insert(self):
        if not self.status:
            self.status = "Draft"

    def validate(self):
        self.total_sales = float(self.total_sales or 0)
        self.total_returns = float(self.total_returns or 0)
        self.net_total = float(self.net_total or 0)

    def on_submit(self):
        self.status = "Closed"
        self.closed_on = now_datetime()
