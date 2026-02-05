import frappe
from frappe import _
from frappe.utils import now_datetime, getdate

def _get_outlet_from_terminal(terminal: str):
    t = frappe.get_doc("AlphaX POS Terminal", terminal)
    return t.outlet

@frappe.whitelist()
def get_outlet_open_shifts(outlet: str, posting_date: str):
    posting_date = getdate(posting_date)
    return frappe.get_all(
        "AlphaX POS Shift",
        filters={
            "outlet": outlet,
            "status": "Open",
            "opened_on": [">=", posting_date],
        },
        fields=["name","terminal","cashier","opened_on","sales_total","net_total"],
        order_by="opened_on asc",
        limit_page_length=200
    )

@frappe.whitelist()
def get_day_close_summary(outlet: str, posting_date: str):
    """Z Report summary for a given outlet + date using submitted Sales Invoices."""
    if not outlet:
        frappe.throw(_("Outlet is required"))
    posting_date = getdate(posting_date)

    # Collect shifts for the date (any shift opened on that date)
    shifts = frappe.get_all(
        "AlphaX POS Shift",
        filters={"outlet": outlet},
        fields=["name","status","opened_on","closed_on","sales_total","returns_total","net_total"],
        limit_page_length=500
    )
    shifts_for_date = []
    for s in shifts:
        if s.opened_on and getdate(s.opened_on) == posting_date:
            shifts_for_date.append(s)

    # Sales Invoices posted from our POS orders with same outlet+date
    si_rows = frappe.db.sql(
        """
        select si.name, si.grand_total, si.is_return
        from `tabSales Invoice` si
        where si.docstatus=1
          and si.posting_date=%s
          and si.alphax_pos_terminal is not null
          and si.alphax_pos_order is not null
        """,
        (posting_date,),
        as_dict=True
    )

    total_sales = sum(float(r["grand_total"] or 0) for r in si_rows if int(r.get("is_return") or 0) == 0)
    total_returns = sum(float(r["grand_total"] or 0) for r in si_rows if int(r.get("is_return") or 0) == 1)
    net_total = total_sales - total_returns

    mop_rows = frappe.db.sql(
        """
        select p.mode_of_payment, sum(p.amount) as amt
        from `tabSales Invoice Payment` p
        join `tabSales Invoice` si on si.name=p.parent
        where si.docstatus=1
          and si.posting_date=%s
          and si.alphax_pos_order is not null
        group by p.mode_of_payment
        """,
        (posting_date,),
        as_dict=True
    )

    return {
        "outlet": outlet,
        "posting_date": str(posting_date),
        "shifts": shifts_for_date,
        "totals": {
            "total_sales": total_sales,
            "total_returns": total_returns,
            "net_total": net_total,
        },
        "payments": mop_rows,
        "can_close": all(s.get("status") == "Closed" for s in shifts_for_date) and len(shifts_for_date) > 0,
    }

@frappe.whitelist()
def create_or_get_day_close(outlet: str, posting_date: str):
    posting_date = getdate(posting_date)
    existing = frappe.db.get_value("AlphaX POS Day Close", {"outlet": outlet, "posting_date": posting_date}, "name")
    if existing:
        return {"name": existing}

    doc = frappe.get_doc({
        "doctype": "AlphaX POS Day Close",
        "outlet": outlet,
        "posting_date": posting_date,
        "status": "Draft",
    })
    doc.insert(ignore_permissions=True)
    return {"name": doc.name}

@frappe.whitelist()
def close_day(outlet: str, posting_date: str, notes: str | None = None):
    summary = get_day_close_summary(outlet, posting_date)
    if not summary.get("can_close"):
        frappe.throw(_("All shifts must be closed before Day Close."))

    dc = create_or_get_day_close(outlet, posting_date)["name"]
    doc = frappe.get_doc("AlphaX POS Day Close", dc)
    if doc.docstatus == 1:
        return {"name": doc.name, "already_closed": 1}

    doc.total_sales = summary["totals"]["total_sales"]
    doc.total_returns = summary["totals"]["total_returns"]
    doc.net_total = summary["totals"]["net_total"]
    doc.notes = notes
    doc.flags.ignore_permissions = True
    doc.save()
    doc.submit()  # marks closed
    return {"name": doc.name, "already_closed": 0}
