import frappe
from frappe import _
from frappe.utils import now_datetime

def _make_sales_invoice_from_order(order):
    """Create an ERPNext Sales Invoice (POS) from an AlphaX POS Order."""
    if not order.items:
        frappe.throw(_("Order has no items."))

    terminal = frappe.get_doc("AlphaX POS Terminal", order.terminal) if order.terminal else None

    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": order.customer or (terminal.default_customer if terminal else None),
        "posting_date": order.posting_date,
        "posting_time": order.posting_time,
        "set_posting_time": 1,
        "is_pos": 1,
        "update_stock": int(order.update_stock or 0),
        "company": order.company or (terminal.company if terminal else None),
        "cost_center": order.cost_center,
        "set_warehouse": order.warehouse or (terminal.warehouse if terminal else None),
        "currency": order.currency,
        "selling_price_list": order.selling_price_list or (terminal.selling_price_list if terminal else None),
        "ignore_pricing_rule": int(order.ignore_pricing_rule or 0),
        "remarks": order.remarks,
        "alphax_pos_order": order.name,
        "alphax_pos_terminal": order.terminal,
        "alphax_pos_shift": order.shift,
    })

    for row in order.items:
        si.append("items", {
            "item_code": row.item_code,
            "qty": row.qty,
            "rate": row.rate,
            "discount_percentage": row.discount_percentage,
            "warehouse": row.warehouse or si.set_warehouse,
        })

    for p in order.payments:
        si.append("payments", {
            "mode_of_payment": p.mode_of_payment,
            "amount": p.amount,
            "reference_no": p.reference_no,
            "reference_date": p.reference_date,
        })

    si.flags.ignore_permissions = True
    si.set_missing_values()
    si.calculate_taxes_and_totals()
    si.save()
    si.submit()
    return si

def _recompute_shift_totals(shift_name: str):
    if not shift_name or not frappe.db.exists("AlphaX POS Shift", shift_name):
        return

    rows = frappe.db.sql(
        """
        select o.sales_invoice
        from `tabAlphaX POS Order` o
        where o.shift=%s and o.docstatus=1 and ifnull(o.sales_invoice,'')!=''
        """,
        (shift_name,),
        as_dict=True
    )
    si_names = [r["sales_invoice"] for r in rows if frappe.db.exists("Sales Invoice", r["sales_invoice"])]

    sales_total = 0.0
    returns_total = 0.0
    mop_totals = {}

    if si_names:
        sis = frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", si_names]},
            fields=["name", "grand_total", "is_return", "docstatus"]
        )
        for si in sis:
            if si.get("docstatus") != 1:
                continue
            amt = float(si.get("grand_total") or 0)
            if int(si.get("is_return") or 0) == 1:
                returns_total += amt
            else:
                sales_total += amt

        pay_rows = frappe.db.sql(
            """
            select p.mode_of_payment, sum(p.amount) as amt
            from `tabSales Invoice Payment` p
            where p.parent in %(parents)s
            group by p.mode_of_payment
            """,
            {"parents": si_names},
            as_dict=True
        )
        for pr in pay_rows:
            mop_totals[pr["mode_of_payment"]] = float(pr["amt"] or 0)

    shift = frappe.get_doc("AlphaX POS Shift", shift_name)
    shift.sales_total = sales_total
    shift.returns_total = returns_total
    shift.net_total = sales_total - returns_total

    shift.set("payments", [])
    for mop, amt in mop_totals.items():
        shift.append("payments", {
            "doctype": "AlphaX POS Shift Payment",
            "mode_of_payment": mop,
            "system_amount": amt,
            "counted_amount": 0,
            "difference": 0,
        })

    shift.flags.ignore_permissions = True
    shift.save()

def on_order_submit(doc, method=None):
    if getattr(doc, "sales_invoice", None) and frappe.db.exists("Sales Invoice", doc.sales_invoice):
        _recompute_shift_totals(doc.shift)
        return

    si = _make_sales_invoice_from_order(doc)
    doc.db_set("sales_invoice", si.name, update_modified=False)
    _recompute_shift_totals(doc.shift)

def on_order_cancel(doc, method=None):
    if getattr(doc, "sales_invoice", None) and frappe.db.exists("Sales Invoice", doc.sales_invoice):
        si = frappe.get_doc("Sales Invoice", doc.sales_invoice)
        if si.docstatus == 1:
            si.flags.ignore_permissions = True
            si.cancel()
    _recompute_shift_totals(doc.shift)
