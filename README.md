# AlphaX Master POS (for ERPNext / Frappe v15+)

A **sector-agnostic POS platform** designed to compete in capability with modern POS stacks (Foodics, Syrve, NCR, etc.)
while staying **ERPNext-native** (Sales Invoice, Stock, GL, Loyalty, Pricing Rules, etc.) and extensible for verticals.

## Why this design
- **ERPNext is the system of record** (items, pricing, taxes, customers, stock, accounting).
- POS runs as a **modern web app** (Desk Page / PWA-ready) and talks to ERPNext via **whitelisted APIs**.
- Core POS is **vertical-neutral**; sector packs (Restaurant, Retail, Services) are feature flags + addons.

## MVP scope (this repo ships a working skeleton)
- Outlet / Terminal setup
- Shift open/close (cash float + closing)
- POS Order + items + payments
- Posting engine → creates ERPNext **Sales Invoice (POS)**
- Boot API (terminal config), item search API, submit order API
- Roles + minimal permissions bootstrap (created programmatically)

> This is a retail+shift MVP. You will extend UI/flows and add sector packs iteratively.

## Install
```bash
bench get-app https://github.com/<your-org>/alphax_master_pos
bench --site <site> install-app alphax_master_pos
bench --site <site> migrate
```

## Run
- Desk → **AlphaX Master POS** → **POS Terminal**
- Or open `/app/alphax-pos`

## Roadmap (recommended)
1) **Retail MVP** (barcode, quick sale, returns, promotions)
2) **Restaurant Pack** (tables, KDS, kitchen stations, coursing)
3) **Offline-first PWA** + device integrations (printers, cash drawer, payment terminals)
4) **Multi-company franchising** (central item/price sync, branch autonomy)
5) Compliance: ZATCA receipts, e-invoicing, audit trails



## v0.5.0 Retail Enhancements
- Suspend/Resume sale (draft POS Orders)
- Returns (Credit Note) with Cash Refund or Store Credit option
- Scale barcode rule support (Weight / Price / Both) via AlphaX POS Barcode Rule + Terminal override
- Default walk-in customer: **Cash Customer**

## White-Label v1 (v0.6.0)
- DocType: **AlphaX POS Brand** (logo/colors/receipt header+footer/legal identity)
- DocType: **AlphaX POS Settings** (default brand, Powered-by toggle)
- Brand resolution: Terminal → Outlet → Settings default
- POS UI applies brand theme via CSS variables from boot API
- Receipt HTML uses brand logo/header/footer and optional Powered-by line

## White-Label v2 (v0.7.0)
- Brand-aware landing page (`/pos`)
- Brand-level Powered-by override
- Brand-level ZATCA QR placeholder flag
- Custom domain field (planning-ready)

## v0.8.0 White-Label v3
- Receipt Templates per Brand: AlphaX POS Receipt Template (Sale/Return/Z)
- Notification Templates per Brand: AlphaX POS Notification Template (Email/SMS/WhatsApp)
- Language Packs per Brand: AlphaX POS Language Pack (EN/AR + RTL) loaded at POS boot
