import frappe
from frappe import _
from frappe.utils import formatdate
from alphax_master_pos.pos.brand import resolve_brand, brand_payload, get_settings
from alphax_master_pos.pos.templates import get_receipt_template
from frappe.utils import get_url

@frappe.whitelist()
def get_sales_invoice_receipt_html(sales_invoice: str):
    if not sales_invoice or not frappe.db.exists("Sales Invoice", sales_invoice):
        frappe.throw(_("Sales Invoice not found"))

    si = frappe.get_doc("Sales Invoice", sales_invoice)

    brand = resolve_brand(terminal=getattr(si,'alphax_pos_terminal',None))
    bp = brand_payload(brand) or {}
    settings = get_settings()
    # Powered-by resolution: Brand override > Global
    show_powered = 1
    if settings:
        show_powered = int(getattr(settings,'show_powered_by',1) or 0)
    if brand and getattr(brand,'show_powered_by_override',None) in ('Yes','No'):
        show_powered = 1 if brand.show_powered_by_override == 'Yes' else 0
    items = si.items or []
    pays = si.payments or []

    template_type = 'Return' if int(getattr(si,'is_return',0) or 0)==1 else 'Sale'
    tpl = get_receipt_template((brand.name if brand else None), template_type)


    def esc(s):
        return frappe.utils.escape_html(str(s or ""))

    rows = "".join([
        f"""<tr>
          <td>{esc(i.item_name or i.item_code)}</td>
          <td style='text-align:right;'>{esc(i.qty)}</td>
          <td style='text-align:right;'>{esc(i.rate)}</td>
          <td style='text-align:right;'>{esc(i.amount)}</td>
        </tr>""" for i in items
    ])

    payrows = "".join([
        f"""<tr>
          <td>{esc(p.mode_of_payment)}</td>
          <td style='text-align:right;'>{esc(p.amount)}</td>
        </tr>""" for p in pays
    ])

    # If template is configured, render it with Jinja
    if tpl and (tpl.get("header_html") or tpl.get("body_html") or tpl.get("footer_html")):
        from frappe.utils.jinja import render_template
        ctx = {"si": si, "brand": bp, "items": items, "payments": pays}
        header = render_template(tpl.get("header_html") or "", ctx)
        body = render_template(tpl.get("body_html") or "", ctx)
        footer = render_template(tpl.get("footer_html") or "", ctx)
        html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"/><title>Receipt {esc(si.name)}</title></head>
<body onload="window.print()">
{header}
{body}
{footer}
{('Powered by AlphaX POS' if show_powered else '')}
</body>
</html>"""
        return {"html": html}

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Receipt {esc(si.name)}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 0; padding: 14px; }}
  .h {{ text-align:center; }}
  .muted {{ color:#666; font-size: 12px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  th, td {{ border-bottom:1px dashed #bbb; padding:6px 0; font-size: 12px; }}
  th {{ text-align:left; }}
  .tot td {{ border-bottom: none; }}
</style>
</head>
<body onload="window.print()">
  <div class="h">\n    <div style='margin-bottom:8px;'>\n      {('<img src="%s" style="max-height:60px;"/>' % esc(bp.get('logo_light'))) if bp.get('logo_light') else ''}\n    </div>
    <div style="font-weight:800; font-size:16px;">{esc(bp.get('legal_name') or bp.get('brand_name') or si.company)}</div>
    <div class="muted">{esc(si.company_address_display or '')}</div>
    <div class="muted">{esc(bp.get('receipt_header') or '')}</div>
    <div class="muted">Invoice: {esc(si.name)} · Date: {esc(formatdate(si.posting_date))}</div>
  </div>

  <table>
    <thead>
      <tr><th>Item</th><th style="text-align:right;">Qty</th><th style="text-align:right;">Rate</th><th style="text-align:right;">Amt</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <table class="tot">
    <tr><td><b>Total</b></td><td style="text-align:right;"><b>{esc(si.grand_total)}</b></td></tr>
  </table>

  <div class="muted" style="margin-top:10px;"><b>Payments</b></div>
  <table>
    <tbody>{payrows}</tbody>
  </table>

  {f"<div class='h' style='margin-top:10px;'><img src='{get_url()}/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Invoice&name={esc(si.name)}' style='display:none'/></div>" if int(getattr(brand,'enable_zatca_qr',0) or 0) else ""} 
  <div class="h muted" style="margin-top:14px;">{esc(bp.get('receipt_footer') or 'Thank you!')}</div>
  <div class="h muted" style="margin-top:8px;">{('Powered by AlphaX POS' if show_powered else '')}</div>
</body>
</html>"""
    return {"html": html}
