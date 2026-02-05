import frappe
from frappe import _
from frappe.utils import now_datetime, getdate

def _get_terminal_outlet(terminal: str):
    t = frappe.get_doc("AlphaX POS Terminal", terminal)
    return t, frappe.get_doc("AlphaX POS Outlet", t.outlet) if t.outlet else None

@frappe.whitelist()
def get_open_shift(terminal: str, cashier: str | None = None):
    cashier = cashier or frappe.session.user
    return frappe.db.get_value("AlphaX POS Shift", {"terminal": terminal, "cashier": cashier, "status": "Open"}, "name")

@frappe.whitelist()
def open_shift(terminal: str, opening_float: float = 0):
    cashier = frappe.session.user
    existing = frappe.db.get_value("AlphaX POS Shift", {"terminal": terminal, "cashier": cashier, "status": "Open"}, "name")
    if existing:
        return {"shift": existing, "already_open": 1}

    t, outlet = _get_terminal_outlet(terminal)
    doc = frappe.get_doc({
        "doctype": "AlphaX POS Shift",
        "terminal": terminal,
        "outlet": t.outlet,
        "cashier": cashier,
        "status": "Open",
        "opened_on": now_datetime(),
        "opening_float": opening_float or 0,
    })
    doc.insert(ignore_permissions=True)
    return {"shift": doc.name, "already_open": 0}

@frappe.whitelist()
def close_shift(shift: str, counted_cash: float = 0, payment_counts: list | None = None, notes: str | None = None):
    if not shift or not frappe.db.exists("AlphaX POS Shift", shift):
        frappe.throw(_("Shift not found"))

    doc = frappe.get_doc("AlphaX POS Shift", shift)
    if doc.status == "Closed":
        return {"shift": doc.name, "already_closed": 1}

    # Guardrail: no draft orders allowed
    draft = frappe.db.get_value("AlphaX POS Order", {"shift": doc.name, "docstatus": 0}, "name")
    if draft:
        frappe.throw(_("Cannot close shift while draft POS Orders exist (example: {0}).").format(draft))

    # Recompute totals just before closing (uses linked Sales Invoices)
    from alphax_master_pos.pos.posting import _recompute_shift_totals
    _recompute_shift_totals(doc.name)
    doc = frappe.get_doc("AlphaX POS Shift", shift)

    doc.closing_cash_counted = counted_cash or 0
    doc.notes = notes

    # Apply counted amounts per mode of payment and compute differences
    if payment_counts:
        counts = {c.get("mode_of_payment"): float(c.get("counted_amount") or 0) for c in payment_counts if c.get("mode_of_payment")}
        for row in doc.payments:
            row.counted_amount = counts.get(row.mode_of_payment, float(row.counted_amount or 0))
            row.difference = float(row.counted_amount or 0) - float(row.system_amount or 0)

    doc.status = "Closed"
    doc.closed_on = now_datetime()
    doc.flags.ignore_permissions = True
    doc.save()
    return {"shift": doc.name, "already_closed": 0}

@frappe.whitelist()
def get_shift_summary(shift: str):
    if not shift or not frappe.db.exists("AlphaX POS Shift", shift):
        frappe.throw(_("Shift not found"))
    s = frappe.get_doc("AlphaX POS Shift", shift)
    return {
        "name": s.name,
        "terminal": s.terminal,
        "cashier": s.cashier,
        "status": s.status,
        "opened_on": s.opened_on,
        "closed_on": s.closed_on,
        "opening_float": s.opening_float,
        "closing_cash_counted": s.closing_cash_counted,
        "sales_total": s.sales_total,
        "returns_total": s.returns_total,
        "net_total": s.net_total,
        "payments": [
            {
                "mode_of_payment": p.mode_of_payment,
                "system_amount": p.system_amount,
                "counted_amount": p.counted_amount,
                "difference": p.difference,
            } for p in s.payments
        ],
    }

@frappe.whitelist()
def get_shift_orders(shift: str, limit: int = 50):
    limit = min(int(limit or 50), 200)
    rows = frappe.get_all(
        "AlphaX POS Order",
        filters={"shift": shift, "docstatus": ["in", [0,1,2]]},
        fields=["name","docstatus","posting_date","posting_time","sales_invoice","customer","terminal"],
        order_by="modified desc",
        limit_page_length=limit
    )
    return rows
