import frappe
from frappe import _
from frappe.utils import getdate

def _require_role(role: str):
    if role not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("Permission denied. Requires role: {0}").format(role))

@frappe.whitelist()
def list_suspended_orders(terminal: str, shift: str | None = None, cashier: str | None = None, limit: int = 50):
    limit = min(int(limit or 50), 200)
    cashier = cashier or frappe.session.user
    filters = {"terminal": terminal, "docstatus": 0, "cashier": cashier}
    if shift:
        filters["shift"] = shift
    rows = frappe.get_all(
        "AlphaX POS Order",
        filters=filters,
        fields=["name","posting_date","posting_time","customer","shift","terminal","modified"],
        order_by="modified desc",
        limit_page_length=limit
    )
    return rows

@frappe.whitelist()
def load_order(order_name: str):
    if not order_name or not frappe.db.exists("AlphaX POS Order", order_name):
        frappe.throw(_("Order not found"))
    doc = frappe.get_doc("AlphaX POS Order", order_name)
    if doc.docstatus != 0:
        frappe.throw(_("Only draft orders can be loaded into cart."))
    return doc.as_dict()

@frappe.whitelist()
def void_draft_order(order_name: str):
    # supervisor required
    _require_role("AlphaX POS Supervisor")
    if not order_name or not frappe.db.exists("AlphaX POS Order", order_name):
        frappe.throw(_("Order not found"))
    doc = frappe.get_doc("AlphaX POS Order", order_name)
    if doc.docstatus != 0:
        frappe.throw(_("Only draft orders can be voided."))
    doc.flags.ignore_permissions = True
    doc.cancel()  # sets docstatus=2
    return {"ok": True}

@frappe.whitelist()
def resolve_scan(scan: str, terminal: str | None = None):
    """Resolve a scanned barcode into {item_code, qty, rate_override} using optional Barcode Rule."""
    scan = (scan or "").strip()
    if not scan:
        return None

    # Basic: direct barcode in Item Barcode
    item = frappe.db.get_value("Item Barcode", {"barcode": scan}, "parent")
    if item:
        return {"item_code": item, "qty": 1, "rate_override": None}

    # Rule-based scale barcode: prefix + item_code + value
    if terminal and frappe.db.exists("AlphaX POS Terminal", terminal):
        t = frappe.get_doc("AlphaX POS Terminal", terminal)
        if getattr(t, "barcode_rule", None) and frappe.db.exists("AlphaX POS Barcode Rule", t.barcode_rule):
            rule = frappe.get_doc("AlphaX POS Barcode Rule", t.barcode_rule)
            if int(rule.enabled or 0) == 1 and scan.startswith(rule.prefix):
                # scan structure: prefix + item_code + value
                start = len(rule.prefix)
                item_code = scan[start:start+int(rule.item_code_length or 0)]
                value_str = scan[start+int(rule.item_code_length or 0): start+int(rule.item_code_length or 0)+int(rule.value_length or 0)]
                if item_code and frappe.db.exists("Item", item_code) and value_str.isdigit():
                    v = float(value_str)
                    mode = (getattr(t, "scale_value_mode_override", None) or rule.value_type or "Weight").strip() or "Weight"
                    if mode == "Weight":
                        qty = v / float(rule.divisor_weight or 1000)
                        return {"item_code": item_code, "qty": qty, "rate_override": None}
                    if mode == "Price":
                        price = v / float(rule.divisor_price or 100)
                        return {"item_code": item_code, "qty": 1, "rate_override": price}
                    # Both: prefer weight unless user later toggles terminal override
                    qty = v / float(rule.divisor_weight or 1000)
                    return {"item_code": item_code, "qty": qty, "rate_override": None}

    return None

@frappe.whitelist()
def create_return_sales_invoice(original_sales_invoice: str, terminal: str, shift: str, mode_of_payment: str | None = None, refund_mode: str = "Store Credit"):
    """Create a return (credit note) for a Sales Invoice.
    refund_mode: 'Cash Refund' or 'Store Credit'
    If Cash Refund: attach a negative payment row (simple POS policy).
    """
    if not original_sales_invoice or not frappe.db.exists("Sales Invoice", original_sales_invoice):
        frappe.throw(_("Original Sales Invoice not found"))

    try:
        from erpnext.controllers.sales_and_purchase_return import make_return_doc
    except Exception:
        make_return_doc = None

    if not make_return_doc:
        frappe.throw(_("ERPNext return helper not available."))

    credit = make_return_doc("Sales Invoice", original_sales_invoice)
    credit.is_pos = 1
    credit.update_stock = 1
    credit.alphax_pos_terminal = terminal
    credit.alphax_pos_shift = shift
    credit.remarks = f"Return against {original_sales_invoice}"
    credit.flags.ignore_permissions = True

    # Clear payments, then add based on refund policy
    credit.set("payments", [])

    refund_mode = (refund_mode or "Store Credit").strip()
    if refund_mode == "Cash Refund":
        if not mode_of_payment:
            mode_of_payment = "Cash"
        # Return invoices are usually negative totals; keep payment negative to balance.
        credit.append("payments", {
            "mode_of_payment": mode_of_payment,
            "amount": float(credit.grand_total or 0),  # negative
        })

    credit.save()
    credit.submit()
    return {"sales_invoice": credit.name, "refund_mode": refund_mode}
