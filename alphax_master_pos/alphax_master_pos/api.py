import frappe
from frappe import _
from alphax_master_pos.pos.brand import resolve_brand, brand_payload
from alphax_master_pos.pos.templates import get_language_pack

@frappe.whitelist()
def ping():
    return {"ok": True, "app": "alphax_master_pos"}

@frappe.whitelist()
def get_pos_boot(terminal: str):
    """Return all config required to start the POS UI for a given terminal."""
    if not terminal or not frappe.db.exists("AlphaX POS Terminal", terminal):
        frappe.throw(_("Terminal not found."))

    t = frappe.get_doc("AlphaX POS Terminal", terminal)
    outlet = frappe.get_doc("AlphaX POS Outlet", t.outlet) if getattr(t, "outlet", None) else None

    # Minimal payload: extend as you add features (printers, taxes, offers, etc.)
    return {
        "terminal": {
            "name": t.name,
            "outlet": t.outlet,
            "warehouse": getattr(t, "warehouse", None),
            "company": getattr(t, "company", None),
            "price_list": getattr(t, "selling_price_list", None),
            "default_customer": getattr(t, "default_customer", None) or "Cash Customer",
            "allow_negative_stock": int(getattr(t, "allow_negative_stock", 0) or 0),
            "barcode_rule": getattr(t, "barcode_rule", None),
            "scale_value_mode_override": getattr(t, "scale_value_mode_override", None),
            "max_discount_without_approval": float(getattr(t, "max_discount_without_approval", 0) or 0),
        },
        "outlet": {
            "name": outlet.name if outlet else None,
            "branch": getattr(outlet, "branch", None) if outlet else None,
            "cost_center": getattr(outlet, "cost_center", None) if outlet else None,
        } if outlet else None,
        "brand": brand_payload(resolve_brand(terminal=t.name, outlet=t.outlet, company=getattr(t,"company",None))),
        "lang_pack": _get_lang_pack_for_terminal(t.name, t.outlet),
        "meta": {
            "user": frappe.session.user,
            "currency": frappe.defaults.get_global_default("currency"),
        }
    }

@frappe.whitelist()
def search_items(search: str = "", limit: int = 30, price_list: str | None = None):
    """Simple item search for MVP. Replace with a smarter search (barcodes, variants, warehouse stock)."""
    limit = min(int(limit or 30), 200)

    filters = {"disabled": 0, "is_sales_item": 1}
    # basic: search by item_code / item_name
    items = frappe.get_all(
        "Item",
        filters=filters,
        fields=["name", "item_code", "item_name", "stock_uom", "image"],
        or_filters=[
            {"item_code": ["like", f"%{search}%"]},
            {"item_name": ["like", f"%{search}%"]},
            {"name": ["like", f"%{search}%"]},
        ] if search else None,
        limit_page_length=limit,
        order_by="modified desc",
    )

    # price lookup (optional)
    if price_list:
        prices = frappe.get_all(
            "Item Price",
            filters={"price_list": price_list, "item_code": ["in", [i["item_code"] for i in items]]},
            fields=["item_code", "price_list_rate"],
            limit_page_length=500,
        )
        price_map = {p["item_code"]: p["price_list_rate"] for p in prices}
        for i in items:
            i["rate"] = price_map.get(i["item_code"])
    return items

@frappe.whitelist()
def create_order(payload: dict):
    """Create a draft AlphaX POS Order (DocType). UI can call this to reserve an order number."""
    payload = payload or {}
    # attach cashier
    payload.setdefault("cashier", frappe.session.user)

    # auto attach open shift for terminal+cashier if not provided
    terminal = payload.get("terminal")
    if terminal and not payload.get("shift"):
        shift = frappe.db.get_value(
            "AlphaX POS Shift",
            {"terminal": terminal, "cashier": frappe.session.user, "status": "Open"},
            "name"
        )
        if shift:
            payload["shift"] = shift

    doc = frappe.get_doc({"doctype": "AlphaX POS Order", **payload})
    doc.insert(ignore_permissions=True)
    return {"name": doc.name}

@frappe.whitelist()
def submit_order(order_name: str):
    """Submit order; server-side posting engine will create Sales Invoice."""
    if not order_name or not frappe.db.exists("AlphaX POS Order", order_name):
        frappe.throw(_("Order not found"))
    doc = frappe.get_doc("AlphaX POS Order", order_name)
    doc.submit()
    return {"ok": True, "order": doc.name, "sales_invoice": getattr(doc, "sales_invoice", None)}


@frappe.whitelist(allow_guest=True)
def get_public_brand():
    brand = resolve_brand()
    return brand_payload(brand)


def _get_lang_pack_for_terminal(terminal: str, outlet: str | None = None):
    b = resolve_brand(terminal=terminal, outlet=outlet)
    bp = brand_payload(b) or {}
    lang = bp.get("language") or "English"
    pack = get_language_pack((b.name if b else None), lang)
    if not pack:
        return None
    import json as _json
    translations = {}
    try:
        translations = _json.loads(pack.get("translations_json") or "{}")
    except Exception:
        translations = {}
    return {"is_rtl": int(pack.get("is_rtl") or 0), "translations": translations}
