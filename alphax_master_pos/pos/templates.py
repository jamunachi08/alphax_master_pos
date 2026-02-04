import frappe

def get_receipt_template(brand: str | None, template_type: str):
    filters = {"enabled": 1, "template_type": template_type}
    if brand:
        filters["brand"] = brand
        t = frappe.get_all("AlphaX POS Receipt Template", filters=filters, fields=["name","header_html","body_html","footer_html","enable_zatca_qr"], limit_page_length=1)
        if t:
            return t[0]
    # fallback: template with no brand set
    t = frappe.get_all("AlphaX POS Receipt Template", filters={"enabled":1,"template_type":template_type, "brand":["is","not set"]}, fields=["name","header_html","body_html","footer_html","enable_zatca_qr"], limit_page_length=1)
    if t:
        return t[0]
    return None

def get_language_pack(brand: str | None, language: str | None):
    if not language:
        return None
    filters = {"enabled": 1, "language": language}
    if brand:
        filters["brand"] = brand
        r = frappe.get_all("AlphaX POS Language Pack", filters=filters, fields=["name","is_rtl","translations_json"], limit_page_length=1)
        if r:
            return r[0]
    r = frappe.get_all("AlphaX POS Language Pack", filters={"enabled":1,"language":language, "brand":["is","not set"]}, fields=["name","is_rtl","translations_json"], limit_page_length=1)
    if r:
        return r[0]
    return None
