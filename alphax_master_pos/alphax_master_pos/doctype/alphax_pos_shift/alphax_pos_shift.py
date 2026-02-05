import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class AlphaXPOSShift(Document):
    def before_insert(self):
        if not self.opened_on:
            self.opened_on = now_datetime()
        if not self.status:
            self.status = "Open"

    def validate(self):
        # compute denomination amounts
        for d in self.cash_denoms or []:
            d.amount = float(d.denomination or 0) * int(d.qty or 0)

        # compute payment differences
        for p in self.payments or []:
            p.system_amount = float(p.system_amount or 0)
            p.counted_amount = float(p.counted_amount or 0)
            p.difference = p.counted_amount - p.system_amount
