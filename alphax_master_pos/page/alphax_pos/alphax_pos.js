frappe.pages['alphax-pos'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'AlphaX Retail POS',
    single_column: true
  });

  page.main.html(`
    <div class="alphax-pos ax-pos">
      <div class="ax-left">
        <div class="ax-card">
          <div class="ax-row">
            <div class="ax-grow">
              <label class="control-label">Terminal</label>
              <input type="text" class="form-control" id="ax_terminal" placeholder="AlphaX POS Terminal">
            </div>
            <div class="ax-grow">
              <label class="control-label">Price List</label>
              <input type="text" class="form-control" id="ax_price_list" placeholder="(optional)">
            </div>
            <div style="display:flex; gap:8px; align-items:end;">
              <button class="btn btn-secondary" id="ax_btn_boot">Load</button>
              <button class="btn btn-primary" id="ax_btn_open_shift">Open Shift</button>
              <button class="btn btn-outline-danger" id="ax_btn_close_shift">Close Shift</button>
            </div>
          </div>
          <div class="ax-row mt-2">
            <span class="ax-muted" id="ax_boot_meta">Not loaded</span>
            <span class="ax-shift-badge" id="ax_shift_badge">Shift: -</span>
          </div>
        </div>

        <div class="ax-card">
          <div class="ax-row">
            <div class="ax-grow">
              <input type="text" class="form-control" placeholder="Scan / search item code or name..." id="ax_search">
            </div>
            <button class="btn btn-primary" id="ax_btn_search">Search</button>
            <button class="btn btn-outline-secondary" id="ax_btn_clear">Clear</button>
          </div>
          <div class="ax-items mt-3" id="ax_items" style="height: 58vh;"></div>
        </div>
      </div>

      <div class="ax-right">
        <div class="ax-card">
          <div class="ax-row">
            <div class="ax-grow">
              <label class="control-label">Customer</label>
              <input type="text" class="form-control" id="ax_customer" placeholder="Walk-in (blank uses terminal default)">
            </div>
          </div>

          <div class="ax-cart mt-3" id="ax_cart" style="height: 42vh;"></div>

          <div class="ax-totalbar mt-2">
            <div>
              <div class="ax-muted">Total</div>
              <div class="ax-total" id="ax_total">0.00</div>
            </div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-outline-secondary" id="ax_btn_suspend">Suspend</button>
              <button class="btn btn-outline-secondary" id="ax_btn_resume">Resume</button>
              <button class="btn btn-outline-warning" id="ax_btn_return">Return</button>
              <button class="btn btn-success" id="ax_btn_pay">Pay</button>
            </div>
          </div>
          <div class="ax-muted mt-2" id="ax_last_msg"></div>
        </div>

        <div class="ax-card">
          <div class="ax-row">
            <div class="ax-grow">
              <label class="control-label">Payment Mode</label>
              <input type="text" class="form-control" id="ax_mop" value="Cash">
            </div>
            <div class="ax-grow">
              <label class="control-label">Paid Amount</label>
              <input type="number" class="form-control" id="ax_pay_amount" value="0" step="0.01">
            </div>
          </div>
          <div class="ax-row mt-2">
            <button class="btn btn-outline-primary" id="ax_btn_exact">Exact</button>
            <button class="btn btn-outline-primary" data-add="5">+5</button>
            <button class="btn btn-outline-primary" data-add="10">+10</button>
            <button class="btn btn-outline-primary" data-add="50">+50</button>
          </div>
          <div class="ax-muted mt-2">Tip: press Enter in search to add first matched item (barcode flow).</div>
        </div>

        <div class="ax-card">
          <div class="ax-row">
            <button class="btn btn-outline-secondary" id="ax_btn_shift_report">Shift Report</button>
            <button class="btn btn-outline-secondary" id="ax_btn_day_close">Day Close (Z)</button>
            <button class="btn btn-outline-secondary" id="ax_btn_print_last">Print Last</button>
            <button class="btn btn-outline-secondary" id="ax_btn_refresh_shift">Refresh Shift</button>
          </div>
          <div class="ax-muted mt-2" id="ax_shift_meta">-</div>
          <div id="ax_shift_payments" class="mt-2"></div>
        </div>
      </div>
    </div>
  `);

  let boot = null;
  let cart = [];
  let shift = null;
  let last_sales_invoice = null;
  let ax_tr = {};
  let ax_rtl = 0;
  function ax_t(k){ return (ax_tr && ax_tr[k]) ? ax_tr[k] : k; }
  let last_search_results = [];

  const money = (v) => (Math.round((v || 0) * 100) / 100).toFixed(2);

  function setMsg(t) {
    page.main.find('#ax_last_msg').text(t || '');
  }

  function cartTotal() {
    return cart.reduce((s, r) => s + (r.qty * r.rate), 0);
  }

  function renderItems(items) {
    const el = page.main.find('#ax_items');
    el.empty();
    if (!items || !items.length) {
      el.append(`<div class="ax-muted">No items found</div>`);
      return;
    }
    items.forEach(it => {
      const rate = it.rate != null ? money(it.rate) : '-';
      el.append(`
        <div class="ax-item" data-item="${frappe.utils.escape_html(it.item_code)}" data-rate="${it.rate || 0}">
          <div class="code">${frappe.utils.escape_html(it.item_code)}</div>
          <div class="name">${frappe.utils.escape_html(it.item_name || it.item_code)}</div>
          <div class="ax-row" style="justify-content:space-between;">
            <div class="ax-muted">UOM: ${frappe.utils.escape_html(it.stock_uom || '')}</div>
            <div class="rate">${rate}</div>
          </div>
        </div>
      `);
    });
  }

  function renderCart() {
    const el = page.main.find('#ax_cart');
    el.empty();

    if (!cart.length) {
      el.append(`<div class="ax-muted">Cart is empty</div>`);
    } else {
      el.append(`
        <table>
          <thead>
            <tr>
              <th style="width:46%;">Item</th>
              <th style="width:20%;" class="text-right">Rate</th>
              <th style="width:22%;">Qty</th>
              <th style="width:12%;" class="text-right"></th>
            </tr>
          </thead>
          <tbody id="ax_cart_rows"></tbody>
        </table>
      `);

      const tbody = el.find('#ax_cart_rows');
      cart.forEach((row, idx) => {
        tbody.append(`
          <tr>
            <td><b>${frappe.utils.escape_html(row.item_code)}</b></td>
            <td class="text-right">${money(row.rate)}</td>
            <td>
              <div class="ax-qty">
                <button class="btn btn-xs btn-default" data-qtyminus="${idx}">-</button>
                <input type="number" class="form-control input-xs" data-qty="${idx}" value="${row.qty}" min="0" step="1">
                <button class="btn btn-xs btn-default" data-qtyplus="${idx}">+</button>
              </div>
            </td>
            <td class="text-right">
              <button class="btn btn-xs btn-outline-danger" data-rm="${idx}">✕</button>
            </td>
          </tr>
        `);
      });
    }

    const total = cartTotal();
    page.main.find('#ax_total').text(money(total));
    page.main.find('#ax_pay_amount').val(money(total));
  }

  async function refreshShift() {
    const terminal = page.main.find('#ax_terminal').val();
    if (!terminal) return;
    shift = await frappe.call('alphax_master_pos.pos.shift.get_open_shift', { terminal }).then(r => r.message);
    page.main.find('#ax_shift_badge').text(`Shift: ${shift || '-'}`);

    if (shift) {
      const sum = await frappe.call('alphax_master_pos.pos.shift.get_shift_summary', { shift }).then(r => r.message);
      page.main.find('#ax_shift_meta').text(`Cashier: ${sum.cashier} · Status: ${sum.status} · Net: ${money(sum.net_total)}`);
      const payEl = page.main.find('#ax_shift_payments');
      payEl.empty();
      if (sum.payments && sum.payments.length) {
        sum.payments.forEach(p => {
          payEl.append(`<div class="ax-row" style="justify-content:space-between; border-bottom:1px solid var(--border-color); padding:6px 0;">
            <div><b>${frappe.utils.escape_html(p.mode_of_payment)}</b></div>
            <div class="ax-muted">System: ${money(p.system_amount)}</div>
          </div>`);
        });
      } else {
        payEl.append(`<div class="ax-muted">No payments yet for this shift.</div>`);
      }
    } else {
      page.main.find('#ax_shift_meta').text('-');
      page.main.find('#ax_shift_payments').html('');
    }
  }

  // LOAD terminal config
  page.main.on('click', '#ax_btn_boot', async () => {
    const terminal = page.main.find('#ax_terminal').val();
    if (!terminal) return frappe.msgprint('Enter terminal name');
    boot = await frappe.call('alphax_master_pos.api.get_pos_boot', { terminal }).then(r => r.message);
    page.main.find('#ax_boot_meta').text(`Loaded: ${boot.terminal.name} · Outlet: ${boot.terminal.outlet || '-'} · Price List: ${boot.terminal.price_list || '-'}`);
    if (boot.terminal.price_list) page.main.find('#ax_price_list').val(boot.terminal.price_list);

    // Apply brand theme (white-label)
    if (boot.brand) {
      const b = boot.brand;
      const rootEl = document.documentElement;
      if (b.primary_color) rootEl.style.setProperty('--ax-primary', b.primary_color);
      if (b.secondary_color) rootEl.style.setProperty('--ax-secondary', b.secondary_color);
      if (b.accent_color) rootEl.style.setProperty('--ax-accent', b.accent_color);
      if (b.font_family) rootEl.style.setProperty('--ax-font', b.font_family);
      // Update page title
      page.set_title(`${b.brand_name || 'POS'} · Retail`);
    }

    await refreshShift();
    setMsg('Ready.');
  });

  // SHIFT open/close
  page.main.on('click', '#ax_btn_open_shift', async () => {
    const terminal = page.main.find('#ax_terminal').val();
    if (!terminal) return frappe.msgprint('Enter terminal and Load');
    const opening = await frappe.prompt([{fieldtype:'Currency', fieldname:'opening_float', label:'Opening Float', default:0}], 'Open Shift', 'Open');
    const res = await frappe.call('alphax_master_pos.pos.shift.open_shift', { terminal, opening_float: opening.opening_float }).then(r=>r.message);

    // Apply brand theme (white-label)
    if (boot.brand) {
      const b = boot.brand;
      const rootEl = document.documentElement;
      if (b.primary_color) rootEl.style.setProperty('--ax-primary', b.primary_color);
      if (b.secondary_color) rootEl.style.setProperty('--ax-secondary', b.secondary_color);
      if (b.accent_color) rootEl.style.setProperty('--ax-accent', b.accent_color);
      if (b.font_family) rootEl.style.setProperty('--ax-font', b.font_family);
      // Update page title
      page.set_title(`${b.brand_name || 'POS'} · Retail`);
    }

    await refreshShift();
    setMsg(res.already_open ? 'Shift already open.' : 'Shift opened.');
  });

  page.main.on('click', '#ax_btn_close_shift', async () => {
    if (!shift) return frappe.msgprint('No open shift to close');
    // load summary for counted amounts
    const sum = await frappe.call('alphax_master_pos.pos.shift.get_shift_summary', { shift }).then(r => r.message);
    const fields = [
      {fieldtype:'Currency', fieldname:'counted_cash', label:'Counted Cash', default: sum.closing_cash_counted || 0},
      {fieldtype:'Small Text', fieldname:'notes', label:'Notes'},
    ];
    // Build a simple JSON editor-like input for payment counts
    fields.push({fieldtype:'Section Break', label:'Payment Counts'});
    (sum.payments || []).forEach((p, idx) => {
      fields.push({fieldtype:'Currency', fieldname:`mop_${idx}`, label:`${p.mode_of_payment} (Counted)`, default: p.counted_amount || 0});
    });

    const values = await frappe.prompt(fields, 'Close Shift', 'Close');
    const payment_counts = (sum.payments || []).map((p, idx) => ({
      mode_of_payment: p.mode_of_payment,
      counted_amount: values[`mop_${idx}`] || 0
    }));
    await frappe.call('alphax_master_pos.pos.shift.close_shift', {
      shift,
      counted_cash: values.counted_cash || 0,
      payment_counts,
      notes: values.notes || null
    });

    // Apply brand theme (white-label)
    if (boot.brand) {
      const b = boot.brand;
      const rootEl = document.documentElement;
      if (b.primary_color) rootEl.style.setProperty('--ax-primary', b.primary_color);
      if (b.secondary_color) rootEl.style.setProperty('--ax-secondary', b.secondary_color);
      if (b.accent_color) rootEl.style.setProperty('--ax-accent', b.accent_color);
      if (b.font_family) rootEl.style.setProperty('--ax-font', b.font_family);
      // Update page title
      page.set_title(`${b.brand_name || 'POS'} · Retail`);
    }

    await refreshShift();
    setMsg('Shift closed.');
  });

  // SEARCH items (Enter to search and add first)
  async function doSearch(addFirst=false) {
    const search = page.main.find('#ax_search').val();
    const price_list = page.main.find('#ax_price_list').val();
    // Try resolve scanned barcode (fast path)
    let resolved = null;
    if (search && /^[0-9]+$/.test(search)) {
      resolved = await frappe.call('alphax_master_pos.pos.retail_api.resolve_scan', { scan: search, terminal: page.main.find('#ax_terminal').val() }).then(r=>r.message);
    }
    if (resolved && resolved.item_code) {
      // fetch item rate if not provided
      const rate = (resolved.rate_override != null) ? resolved.rate_override : 0;
      addToCart(resolved.item_code, rate, resolved.qty || 1);
      page.main.find('#ax_search').val('');
      setMsg(`Added (scan): ${resolved.item_code}`);
      return;
    }

    const items = await frappe.call('alphax_master_pos.api.search_items', { search, price_list, limit: 60 }).then(r => r.message);
    last_search_results = items || [];
    renderItems(items);
    if (addFirst && last_search_results.length) {
      const it = last_search_results[0];
      addToCart(it.item_code, it.rate || 0);
      page.main.find('#ax_search').val('');
      setMsg(`Added: ${it.item_code}`);
    }
  }

  page.main.on('click', '#ax_btn_search', async () => doSearch(false));
  page.main.on('keydown', '#ax_search', async (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      await doSearch(true);
    }
  });

  page.main.on('click', '#ax_btn_clear', () => {
    page.main.find('#ax_search').val('');
    renderItems([]);
  });

  function addToCart(item_code, rate, qty=1) {
    const existing = cart.find(r => r.item_code === item_code && r.rate === rate);
    if (existing) existing.qty += (qty || 1);
    else cart.push({ item_code, qty: (qty || 1), rate: parseFloat(rate || 0) || 0, discount_percentage: 0 });
    renderCart();
  }

  // click item card to add
  page.main.on('click', '.ax-item', (e) => {
    const card = $(e.currentTarget);
    addToCart(card.attr('data-item'), card.attr('data-rate'));
  });

  // cart qty changes
  page.main.on('click', 'button[data-qtyminus]', (e) => {
    const idx = parseInt($(e.currentTarget).attr('data-qtyminus'), 10);
    cart[idx].qty = Math.max(0, (cart[idx].qty || 0) - 1);
    cart = cart.filter(r => r.qty > 0);
    renderCart();
  });
  page.main.on('click', 'button[data-qtyplus]', (e) => {
    const idx = parseInt($(e.currentTarget).attr('data-qtyplus'), 10);
    cart[idx].qty = (cart[idx].qty || 0) + 1;
    renderCart();
  });
  page.main.on('change', 'input[data-qty]', (e) => {
    const idx = parseInt($(e.currentTarget).attr('data-qty'), 10);
    cart[idx].qty = Math.max(0, parseFloat($(e.currentTarget).val() || '0') || 0);
    cart = cart.filter(r => r.qty > 0);
    renderCart();
  });
  page.main.on('click', 'button[data-rm]', (e) => {
    const idx = parseInt($(e.currentTarget).attr('data-rm'), 10);
    cart.splice(idx, 1);
    renderCart();
  });

  // payment helpers
  page.main.on('click', '#ax_btn_exact', () => {
    page.main.find('#ax_pay_amount').val(money(cartTotal()));
  });
  page.main.on('click', 'button[data-add]', (e) => {
    const add = parseFloat($(e.currentTarget).attr('data-add')) || 0;
    const cur = parseFloat(page.main.find('#ax_pay_amount').val() || '0') || 0;
    page.main.find('#ax_pay_amount').val(money(cur + add));
  });


  // Suspend: create draft order and clear cart (keeps shift linkage)
  page.main.on('click', '#ax_btn_suspend', async () => {
    const terminal = page.main.find('#ax_terminal').val();
    if (!boot || !terminal) return frappe.msgprint('Load terminal first');
    if (!shift) return frappe.msgprint('Open shift first');
    if (!cart.length) return frappe.msgprint('Cart is empty');

    const customer = page.main.find('#ax_customer').val();
    const order_payload = {
      terminal,
      shift,
      customer: customer || null,
      posting_date: frappe.datetime.get_today(),
      posting_time: frappe.datetime.now_time(),
      company: boot?.terminal?.company || null,
      warehouse: boot?.terminal?.warehouse || null,
      selling_price_list: boot?.terminal?.price_list || null,
      currency: boot?.meta?.currency || null,
      update_stock: 1,
      items: cart.map(r => ({doctype: "AlphaX POS Order Item", ...r})),
      payments: [],
    };
    const created = await frappe.call('alphax_master_pos.api.create_order', { payload: order_payload }).then(r => r.message);
    setMsg(`Suspended: ${created.name}`);
    cart = [];
    renderCart();
  });

  // Resume: list suspended draft orders and load into cart
  page.main.on('click', '#ax_btn_resume', async () => {
    const terminal = page.main.find('#ax_terminal').val();
    if (!boot || !terminal) return frappe.msgprint('Load terminal first');
    if (!shift) return frappe.msgprint('Open shift first');

    const rows = await frappe.call('alphax_master_pos.pos.retail_api.list_suspended_orders', { terminal, shift, limit: 50 }).then(r=>r.message);
    if (!rows || !rows.length) return frappe.msgprint('No suspended orders found.');

    const options = rows.map(x => `${x.name} · ${x.customer || '-'} · ${x.posting_time || ''}`);
    const pick = await frappe.prompt([{fieldtype:'Select', fieldname:'order', label:'Select Suspended Order', options: options.join('\n')}], 'Resume Order', 'Load');
    const order_name = (pick.order || '').split(' · ')[0].trim();
    const doc = await frappe.call('alphax_master_pos.pos.retail_api.load_order', { order_name }).then(r=>r.message);

    // load cart
    cart = (doc.items || []).map(i => ({ item_code: i.item_code, qty: i.qty, rate: i.rate, discount_percentage: i.discount_percentage || 0 }));
    page.main.find('#ax_customer').val(doc.customer || '');
    renderCart();
    setMsg(`Resumed: ${doc.name}`);
  });

  // Return: create credit note against a Sales Invoice
  page.main.on('click', '#ax_btn_return', async () => {
    const terminal = page.main.find('#ax_terminal').val();
    if (!boot || !terminal) return frappe.msgprint('Load terminal first');
    if (!shift) return frappe.msgprint('Open shift first');

    const v = await frappe.prompt([
      {fieldtype:'Data', fieldname:'invoice', label:'Original Sales Invoice', reqd:1},
      {fieldtype:'Select', fieldname:'refund_mode', label:'Refund Mode', options:'Cash Refund\nStore Credit', default:'Store Credit', reqd:1},
      {fieldtype:'Data', fieldname:'mop', label:'Mode of Payment (for Cash Refund)', default:'Cash'},
    ], 'Return / Refund', 'Create Return');

    const res = await frappe.call('alphax_master_pos.pos.retail_api.create_return_sales_invoice', {
      original_sales_invoice: v.invoice,
      terminal,
      shift,
      mode_of_payment: v.mop || 'Cash',
      refund_mode: v.refund_mode || 'Store Credit'
    }).then(r=>r.message);

    frappe.msgprint(`Return created: ${res.sales_invoice} (${res.refund_mode})`);

    // Apply brand theme (white-label)
    if (boot.brand) {
      const b = boot.brand;
      const rootEl = document.documentElement;
      if (b.primary_color) rootEl.style.setProperty('--ax-primary', b.primary_color);
      if (b.secondary_color) rootEl.style.setProperty('--ax-secondary', b.secondary_color);
      if (b.accent_color) rootEl.style.setProperty('--ax-accent', b.accent_color);
      if (b.font_family) rootEl.style.setProperty('--ax-font', b.font_family);
      // Update page title
      page.set_title(`${b.brand_name || 'POS'} · Retail`);
    }

    await refreshShift();
  });


  // Pay
  page.main.on('click', '#ax_btn_pay', async () => {
    const terminal = page.main.find('#ax_terminal').val();
    if (!boot || !terminal) return frappe.msgprint('Load terminal first');
    if (!shift) return frappe.msgprint('Open shift first');
    if (!cart.length) return frappe.msgprint('Cart is empty');

    const customer = page.main.find('#ax_customer').val();
    const mop = page.main.find('#ax_mop').val() || 'Cash';
    const amount = parseFloat(page.main.find('#ax_pay_amount').val() || '0') || 0;
    const total = cartTotal();

    if (amount <= 0) return frappe.msgprint('Enter paid amount');
    if (amount + 0.0001 < total) return frappe.msgprint('Paid amount is less than total (partial payments not enabled in this MVP).');

    const order_payload = {
      terminal,
      shift,
      customer: customer || null,
      posting_date: frappe.datetime.get_today(),
      posting_time: frappe.datetime.now_time(),
      company: boot?.terminal?.company || null,
      warehouse: boot?.terminal?.warehouse || null,
      selling_price_list: boot?.terminal?.price_list || null,
      currency: boot?.meta?.currency || null,
      update_stock: 1,
      items: cart.map(r => ({doctype: "AlphaX POS Order Item", ...r})),
      payments: [{doctype: "AlphaX POS Payment", mode_of_payment: mop, amount: total}],
    };

    const created = await frappe.call('alphax_master_pos.api.create_order', { payload: order_payload }).then(r => r.message);
    const submitted = await frappe.call('alphax_master_pos.api.submit_order', { order_name: created.name }).then(r => r.message);

    last_sales_invoice = submitted.sales_invoice || null;
    setMsg(`Submitted. Order: ${submitted.order} · Sales Invoice: ${submitted.sales_invoice || '-'}`);
    cart = [];
    renderCart();

    // Apply brand theme (white-label)
    if (boot.brand) {
      const b = boot.brand;
      const rootEl = document.documentElement;
      if (b.primary_color) rootEl.style.setProperty('--ax-primary', b.primary_color);
      if (b.secondary_color) rootEl.style.setProperty('--ax-secondary', b.secondary_color);
      if (b.accent_color) rootEl.style.setProperty('--ax-accent', b.accent_color);
      if (b.font_family) rootEl.style.setProperty('--ax-font', b.font_family);
      // Update page title
      page.set_title(`${b.brand_name || 'POS'} · Retail`);
    }

    await refreshShift();
  });

  // Reports
  page.main.on('click', '#ax_btn_shift_report', async () => {
    if (!shift) return frappe.msgprint('No open shift');
    const orders = await frappe.call('alphax_master_pos.pos.shift.get_shift_orders', { shift, limit: 100 }).then(r=>r.message);
    const sum = await frappe.call('alphax_master_pos.pos.shift.get_shift_summary', { shift }).then(r=>r.message);

    const html = `
      <div>
        <div><b>Shift:</b> ${frappe.utils.escape_html(sum.name)} · <b>Cashier:</b> ${frappe.utils.escape_html(sum.cashier)} · <b>Status:</b> ${sum.status}</div>
        <div class="mt-2"><b>Net:</b> ${money(sum.net_total)} · <b>Sales:</b> ${money(sum.sales_total)} · <b>Returns:</b> ${money(sum.returns_total)}</div>
        <hr/>
        <div><b>Orders:</b> ${orders.length}</div>
        <div style="max-height: 320px; overflow:auto; border:1px solid var(--border-color); border-radius:10px; padding:8px;">
          ${orders.map(o => `<div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border-color); padding:6px 0;">
            <div><b>${o.name}</b> <span class="text-muted">(${o.docstatus==1?'Submitted':o.docstatus==0?'Draft':'Cancelled'})</span></div>
            <div class="text-muted">${o.sales_invoice || '-'}</div>
          </div>`).join('')}
        </div>
      </div>
    `;
    frappe.msgprint({title:'Shift Report (X)', message: html, indicator:'blue'});
  });

  page.main.on('click', '#ax_btn_refresh_shift', async () => {

    // Apply brand theme (white-label)
    if (boot.brand) {
      const b = boot.brand;
      const rootEl = document.documentElement;
      if (b.primary_color) rootEl.style.setProperty('--ax-primary', b.primary_color);
      if (b.secondary_color) rootEl.style.setProperty('--ax-secondary', b.secondary_color);
      if (b.accent_color) rootEl.style.setProperty('--ax-accent', b.accent_color);
      if (b.font_family) rootEl.style.setProperty('--ax-font', b.font_family);
      // Update page title
      page.set_title(`${b.brand_name || 'POS'} · Retail`);
    }

    await refreshShift();
    setMsg('Shift refreshed.');
  });


  // Day Close (Z report)
  page.main.on('click', '#ax_btn_day_close', async () => {
    if (!boot?.terminal?.outlet) return frappe.msgprint('Load terminal first');
    const outlet = boot.terminal.outlet;
    const posting_date = frappe.datetime.get_today();

    const sum = await frappe.call('alphax_master_pos.pos.day_close.get_day_close_summary', { outlet, posting_date }).then(r=>r.message);
    const payhtml = (sum.payments || []).map(p => `<div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border-color); padding:6px 0;">
        <div><b>${frappe.utils.escape_html(p.mode_of_payment)}</b></div>
        <div>${money(p.amt)}</div>
      </div>`).join('') || '<div class="ax-muted">No payments</div>';

    const shhtml = (sum.shifts || []).map(s => `<div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border-color); padding:6px 0;">
        <div><b>${frappe.utils.escape_html(s.name)}</b> <span class="text-muted">(${s.status})</span></div>
        <div class="text-muted">Net: ${money(s.net_total)}</div>
      </div>`).join('') || '<div class="ax-muted">No shifts found for today.</div>';

    const html = `
      <div>
        <div><b>Outlet:</b> ${frappe.utils.escape_html(outlet)} · <b>Date:</b> ${frappe.utils.escape_html(sum.posting_date)}</div>
        <div class="mt-2"><b>Sales:</b> ${money(sum.totals.total_sales)} · <b>Returns:</b> ${money(sum.totals.total_returns)} · <b>Net:</b> ${money(sum.totals.net_total)}</div>
        <hr/>
        <div><b>Shifts</b></div>
        <div style="max-height: 200px; overflow:auto; border:1px solid var(--border-color); border-radius:10px; padding:8px;">${shhtml}</div>
        <div class="mt-3"><b>Payments</b></div>
        <div style="border:1px solid var(--border-color); border-radius:10px; padding:8px;">${payhtml}</div>
        <div class="mt-3">
          <span class="text-muted">Can Close:</span> <b>${sum.can_close ? 'YES' : 'NO'}</b>
        </div>
      </div>
    `;

    frappe.msgprint({
      title: 'Day Close (Z Report)',
      message: html,
      indicator: sum.can_close ? 'green' : 'orange',
      primary_action: sum.can_close ? {
        label: 'Close Day',
        action: async () => {
          const notes = await frappe.prompt([{fieldtype:'Small Text', fieldname:'notes', label:'Notes'}], 'Close Day', 'Close');
          await frappe.call('alphax_master_pos.pos.day_close.close_day', { outlet, posting_date, notes: notes.notes || null });
          frappe.msgprint('Day Close completed.');
        }
      } : null
    });
  });

  // Print last receipt
  page.main.on('click', '#ax_btn_print_last', async () => {
    if (!last_sales_invoice) return frappe.msgprint('No recent invoice to print.');
    const res = await frappe.call('alphax_master_pos.pos.receipt.get_sales_invoice_receipt_html', { sales_invoice: last_sales_invoice }).then(r=>r.message);
    const w = window.open('', '_blank');
    w.document.open();
    w.document.write(res.html);
    w.document.close();
  });

  renderCart();
};
