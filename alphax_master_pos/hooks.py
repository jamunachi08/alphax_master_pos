app_name = "alphax_master_pos"
app_title = "AlphaX Master POS"
app_publisher = "AlphaX"
app_description = "Sector-agnostic Master POS platform for ERPNext / Frappe"
app_email = "support@example.com"
app_license = "MIT"

# We avoid fixtures for Role/Custom Field; create them safely via after_install.
after_install = "alphax_master_pos.alphax_master_pos.install.after_install"

doc_events = {
    "AlphaX POS Order": {
        "on_submit": "alphax_master_pos.alphax_master_pos.pos.posting.on_order_submit",
        "on_cancel": "alphax_master_pos.alphax_master_pos.pos.posting.on_order_cancel",
    }
}

scheduler_events = {
    "daily": [
        "alphax_master_pos.alphax_master_pos.pos.maintenance.daily_cleanup",
    ]
}
