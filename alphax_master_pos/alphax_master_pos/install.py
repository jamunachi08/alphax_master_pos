import frappe

ROLES = [
    "AlphaX POS Cashier",
    "AlphaX POS Supervisor",
    "AlphaX POS Manager",
    "AlphaX POS Kitchen",
]

CUSTOM_FIELDS = [
    # Link to shift
    {
        "dt": "Sales Invoice",
        "fieldname": "alphax_pos_shift",
        "label": "AlphaX POS Shift",
        "fieldtype": "Link",
        "options": "AlphaX POS Shift",
        "insert_after": "alphax_pos_terminal",
        "read_only": 1,
    },
    # Sales Invoice: capture POS metadata
    {
        "dt": "Sales Invoice",
        "fieldname": "alphax_pos_order",
        "label": "AlphaX POS Order",
        "fieldtype": "Link",
        "options": "AlphaX POS Order",
        "insert_after": "pos_profile",
        "read_only": 1,
    },
    {
        "dt": "Sales Invoice",
        "fieldname": "alphax_pos_terminal",
        "label": "AlphaX POS Terminal",
        "fieldtype": "Link",
        "options": "AlphaX POS Terminal",
        "insert_after": "alphax_pos_order",
        "read_only": 1,
    },
]

def _ensure_role(role_name: str):
    if not frappe.db.exists("Role", role_name):
        doc = frappe.get_doc({"doctype": "Role", "role_name": role_name})
        doc.insert(ignore_permissions=True)

def _ensure_custom_field(cf: dict):
    # 'Custom Field' requires a unique name: "{dt}-{fieldname}"
    name = f'{cf["dt"]}-{cf["fieldname"]}'
    if frappe.db.exists("Custom Field", name):
        return
    doc = frappe.get_doc({"doctype": "Custom Field", "name": name, **cf})
    doc.insert(ignore_permissions=True)

def after_install():
    _ensure_singleton_settings()
    _ensure_default_brand()
    for r in ROLES:
        _ensure_role(r)
    for cf in CUSTOM_FIELDS:
        _ensure_custom_field(cf)
    frappe.db.commit()


def _ensure_singleton_settings():
    if not frappe.db.exists("AlphaX POS Settings", "AlphaX POS Settings"):
        doc = frappe.get_doc({"doctype": "AlphaX POS Settings", "name": "AlphaX POS Settings"})
        doc.insert(ignore_permissions=True)

def _ensure_default_brand():
    # Create a minimal default brand if no brand exists
    if frappe.db.count("AlphaX POS Brand") == 0:
        b = frappe.get_doc({
            "doctype": "AlphaX POS Brand",
            "brand_name": "AlphaX",
            "enabled": 1,
            "primary_color": "#1f7ae0",
            "secondary_color": "#0b1f3b",
            "accent_color": "#f59e0b",
        })
        b.insert(ignore_permissions=True)
    # Set default brand on settings if not set
    s = frappe.get_doc("AlphaX POS Settings", "AlphaX POS Settings")
    if not getattr(s, "default_brand", None):
        s.default_brand = frappe.get_all("AlphaX POS Brand", fields=["name"], limit_page_length=1)[0]["name"]
        s.flags.ignore_permissions = True
        s.save()

