import frappe

def get_settings():
    if frappe.db.exists("AlphaX POS Settings", "AlphaX POS Settings"):
        return frappe.get_doc("AlphaX POS Settings", "AlphaX POS Settings")
    return None

def resolve_brand(terminal: str | None = None, outlet: str | None = None, company: str | None = None):
    """Resolve brand with priority Terminal → Outlet → Settings default."""
    # terminal override
    if terminal and frappe.db.exists("AlphaX POS Terminal", terminal):
        t = frappe.get_doc("AlphaX POS Terminal", terminal)
        if getattr(t, "brand", None) and frappe.db.exists("AlphaX POS Brand", t.brand):
            return frappe.get_doc("AlphaX POS Brand", t.brand)

        outlet = outlet or getattr(t, "outlet", None)

    # outlet
    if outlet and frappe.db.exists("AlphaX POS Outlet", outlet):
        o = frappe.get_doc("AlphaX POS Outlet", outlet)
        if getattr(o, "brand", None) and frappe.db.exists("AlphaX POS Brand", o.brand):
            return frappe.get_doc("AlphaX POS Brand", o.brand)

    s = get_settings()
    if s and getattr(s, "default_brand", None) and frappe.db.exists("AlphaX POS Brand", s.default_brand):
        return frappe.get_doc("AlphaX POS Brand", s.default_brand)

    # fallback: first brand
    b = frappe.get_all("AlphaX POS Brand", filters={"enabled": 1}, fields=["name"], limit_page_length=1)
    if b:
        return frappe.get_doc("AlphaX POS Brand", b[0]["name"])
    return None

def brand_payload(brand):
    if not brand:
        return None
    return {
        "name": brand.name,
        "brand_name": getattr(brand, "brand_name", None),
        "logo_light": getattr(brand, "logo_light", None),
        "logo_dark": getattr(brand, "logo_dark", None),
        "primary_color": getattr(brand, "primary_color", None),
        "secondary_color": getattr(brand, "secondary_color", None),
        "accent_color": getattr(brand, "accent_color", None),
        "font_family": getattr(brand, "font_family", None),
        "legal_name": getattr(brand, "legal_name", None),
        "vat_number": getattr(brand, "vat_number", None),
        "cr_number": getattr(brand, "cr_number", None),
        "receipt_header": getattr(brand, "receipt_header", None),
        "receipt_footer": getattr(brand, "receipt_footer", None),
        "support_phone": getattr(brand, "support_phone", None),
        "support_email": getattr(brand, "support_email", None),
        "language": getattr(brand, "language", None),
    }
