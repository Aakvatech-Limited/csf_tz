frappe.ui.form.on("Sales Invoice", {
  refresh: function (frm) {},
  generate_vfd: (frm) => {
    if (!frm.doc.vfd_cust_id) {
      frappe.msgprint({
        title: __("Confirmation Required"),
        message: __("Are you sure you want to send VFD without TIN"),
        primary_action: {
          label: "Proceed",
          action(values) {
            _generate_vfd(frm);
            cur_dialog.cancel();
          },
        },
      });
    } else if (frm.doc.vfd_cust_id && frm.doc.vfd_cust_id != frm.doc.tax_id) {
      frappe.msgprint({
        title: __("Confirmation Required"),
        message: __("TIN an VFD Customer ID mismatch"),
        primary_action: {
          label: "Proceed",
          action(values) {
            _generate_vfd(frm);
            cur_dialog.cancel();
          },
        },
      });
    } else {
      _generate_vfd(frm);
    }
  },
});

function _generate_vfd(frm) {
  frappe.call({
    method: "csf_tz.vfd_support.utils.generate_tra_vfd",
    args: {
      docname: frm.doc.name,
    },
    freeze: true,
    freeze_message: __("Preparing VFD preview..."),
    callback: (r) => {

      let data = r.message.data
      let vfd_provider = r.message.vfd_provider
      let preview = r.message.preview

      if (data && !preview) {
        frm.reload_doc();
        frappe.show_alert({
          message: __("VFD successfully sent to TRA"),
          indicator: "green",
        });
      } else if (data && preview) {
        show_vfd_preview_dialog(frm, data, vfd_provider);
      } else if (!data) {
        frappe.msgprint(__("VFD generation failed"));
      }
    },
    error: () => {
      frappe.msgprint(__("VFD generation failed"));
    },
  });
}

function show_vfd_preview_dialog(frm, payload, vfd_provider) {
  // Some providers (esp. VFDPlus) may return payload as serialized JSON string.
  if (payload && typeof payload === 'string') {
    try {
      payload = JSON.parse(payload);
    } catch (e) {
      // Leave as-is; normalization will handle empty objects safely.
    }
  }
  // Normalize differing payload structures across providers (SimplifyVFD, VFDPlus, TotalVFD)
  function normalizePayload(raw, provider) {
    const p = raw || {};
    // Customer object differences
    let customerObj = p.customer || {};
    if (provider === "VFDPlus") {
      customerObj = p.customer_info || {};
    }

    const customerName = customerObj.name || customerObj.cust_name || customerObj.customerName || '';
    const identificationType = customerObj.identificationType || customerObj.cust_id_type || customerObj.idType || '';
    const identificationNumber = customerObj.identificationNumber || customerObj.cust_id || customerObj.idValue || '';
    const vatRegistrationNumber = customerObj.vatRegistrationNumber || customerObj.cust_vrn || customerObj.vrn || '';

    // Invoice / reference id key differences
    const partnerInvoiceId = p.partnerInvoiceId || p.trans_no || p.referenceNumber || frm.doc.name;
    const invoiceAmountType = p.invoiceAmountType || p.amountType || '';

    // Date / time differences
    let dateTime = p.dateTime || '';
    if (!dateTime) {
      if (provider === "VFDPlus") {
        if (p.idate) {
          dateTime = p.idate + (p.itime ? " " + p.itime : '');
        }
      }
      // TotalVFD sample does not provide date; fallback handled later
    }

    // Items arrays differences
    let items = [];
    if (Array.isArray(p.items)) {
      items = p.items.map(it => ({
        description: it.description || it.name || it.item_name || '',
        quantity: it.quantity || it.qty || it.item_qty || 0,
        unitAmount: it.unitAmount || parseFloat((it.price / (it.qty || 1)).toFixed(2)) || it.usp || 0,
        taxType: (it.taxType || it.vatGroup || it.vat_rate_code || '').toString(),
        _raw: it,
      }));
    } else if (Array.isArray(p.cart_items)) { // VFDPlus
      items = p.cart_items.map(it => ({
        description: it.description || it.item_name || '',
        quantity: it.quantity || it.item_qty || 0,
        unitAmount: it.unitAmount || it.usp || 0,
        taxType: (it.taxType || it.vat_rate_code || '').toString(),
        _raw: it,
      }));
    }

    // Payments arrays differences
    let payments = [];
    if (Array.isArray(p.payments)) {
      payments = p.payments.map(pm => ({
        type: pm.type || pm.pmt_type || '',
        amount: pm.amount || pm.pmt_amount || 0,
      }));
    } else if (Array.isArray(p.payment_methods)) { // VFDPlus
      payments = p.payment_methods.map(pm => ({
        type: pm.type || pm.pmt_type || '',
        amount: pm.amount || pm.pmt_amount || 0,
      }));
    }

    return {
      customerName,
      identificationType,
      identificationNumber,
      vatRegistrationNumber,
      partnerInvoiceId,
      invoiceAmountType,
      dateTime,
      items,
      payments,
    };
  }

  const norm = normalizePayload(payload, vfd_provider);
  const normalizedItems = norm.items || [];
  const normalizedPayments = norm.payments || [];
  const normalizedDateTime = norm.dateTime;

  const formatNumber = (val) =>
    new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(flt(val));

  // Compute totals & taxes (assume STANDARD = 18% VAT, others = 0 for preview purposes)
  let totalIncl = 0;
  let taxAmount = 0;

  (normalizedItems || []).forEach((item) => {
    const lineTotal = (item.unitAmount || 0) * (item.quantity || 0);
    totalIncl += lineTotal;
    const taxCode = (item.taxType || '').toUpperCase();
    const taxRate = ["STANDARD", "A"].includes(taxCode) ? 0.18 : 0;

    if (taxRate) {
      const netLineTotal = flt(lineTotal / (1 + taxRate));
      taxAmount += lineTotal - netLineTotal;
    } 
  });

  let totalExcl = totalIncl - taxAmount;

  // Guard against negative/NaN
  if (totalExcl < 0 || isNaN(totalExcl)) {
    totalExcl = 0;
  }

  if (isNaN(taxAmount)) {
    taxAmount = 0;
  }

  const company_name = (frm.doc.company || "").toUpperCase();
  let receipt_date = ''
  if (normalizedDateTime && !["None", "null", "Invalid date", "undefined"].includes(String(normalizedDateTime))) {
    const dt = frappe.datetime.str_to_obj(normalizedDateTime);
    receipt_date = frappe.datetime.str_to_user(frappe.datetime.obj_to_str(dt, "YYYY-MM-DD"));
  } else {
    receipt_date = frappe.datetime.nowdate();
  }

  // Helpers to conditionally build info rows (omit labels if value absent)
  function buildInfoRow(label, value) {
    const hasVal = value !== undefined && value !== null && String(value).trim() !== '';
    if (!hasVal) return '';
    return `<div class="vfd-row"><span class="vfd-label">${frappe.utils.escape_html(label)}</span><span class="vfd-value">${frappe.utils.escape_html(String(value))}</span></div>`;
  }

  const customerInfoHTML = [
    buildInfoRow("Customer Name:", norm.customerName),
    buildInfoRow("Customer ID Type:", norm.identificationType),
    buildInfoRow("Customer ID:", norm.identificationNumber),
    buildInfoRow("VAT Reg No:", norm.vatRegistrationNumber),
  ].join('');

  const invoiceInfoHTML = [
    buildInfoRow("Tax Type:", norm.invoiceAmountType),
    buildInfoRow("Invoice ID:", norm.partnerInvoiceId || frm.doc.name),
  ].join('');

  const receiptHTML = `
  <div class="vfd-preview-root">
    <style>
      .vfd-preview-root {font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, 'Roboto', 'Helvetica Neue', Arial, sans-serif; max-width:640px; margin:0 auto; font-size:12.5px; color:#222; line-height:1.35;}
      .vfd-center { text-align:center; }
      .vfd-muted { color:#555; }
      .vfd-heading { font-weight:600; letter-spacing:.5px; font-size:12px; text-transform:uppercase; margin:24px 0 6px; }
      .vfd-title { font-size:17px; font-weight:600; margin:0 0 2px; }
      .vfd-subgrid { display:flex; flex-wrap:wrap; gap:16px; margin:4px 0 4px; }
      .vfd-box { flex:1 1 240px; }
      .vfd-row { display:flex; align-items:flex-start; margin:2px 0; }
      .vfd-label { font-weight:500; width:110px; flex:0 0 110px; }
      .vfd-value { flex:1 1 auto; }
      .vfd-topline { border-top:1px solid #e4e6e9; margin:16px 0 0; }
      .vfd-hr { height:1px; background:#e4e6e9; border:0; margin:12px 0 16px; }
      table.vfd-table { width:100%; border-collapse:separate; border-spacing:0; font-size:12px; }
      table.vfd-table thead th { background:#f8f9fa; font-weight:600; padding:6px 8px; border:1px solid #e1e4e8; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
      table.vfd-table tbody td { padding:6px 8px; border:1px solid #eef0f2; vertical-align:top; }
      table.vfd-table tbody tr:nth-child(even) td { background:#fbfcfd; }
      .vfd-totals { margin-top:14px; display:flex; justify-content:flex-end; }
      .vfd-totals-inner { width:300px; }
      .vfd-totals-row { display:flex; justify-content:space-between; padding:5px 0; }
      .vfd-totals-row.border { border-top:1px solid #d9dde2; }
      .vfd-totals-row.emph { font-size:13px; font-weight:600; border-top:1px solid #d9dde2; border-bottom:1px solid #d9dde2; margin-top:4px; }
      .vfd-footer { margin-top:20px; font-size:11px; text-align:center; color:blue; }
      .vfd-receipt-banner { font-weight:600; font-size:12px; letter-spacing:1px; margin:0; }
      .vfd-header { margin-bottom:8px; }
    </style>
    <div class="vfd-center" style="margin-bottom:4px;">
      <div class="vfd-title">${frappe.utils.escape_html(company_name)}</div>
      <div class="vfd-muted" style="font-size:11.5px;">TIN: ${frappe.utils.escape_html(frm.doc.tax_id || '-')}&nbsp;&nbsp;|&nbsp;&nbsp;RECEIPT DATE: ${frappe.utils.escape_html(receipt_date)}</div>
    </div>
    <hr class="vfd-hr" />
    <div class="vfd-subgrid">
      <div class="vfd-box" style="padding-right:20px; font-size:11px;">
        ${customerInfoHTML}
      </div>
      <div class="vfd-box" style="padding-left:40px; border-left:2px solid #e4e6e9; font-size:11px;">
        ${invoiceInfoHTML}
      </div>
    </div>
    <div class="vfd-heading" style="margin-top:18px; text-align:center;">Purchased Items</div>
    <table class="vfd-table">
      <thead>
        <tr>
          <th style="text-align:left;">Description</th>
          <th style="text-align:center; width:60px;">Qty</th>
          <th style="text-align:right; width:110px;">Unit Amount</th>
          <th style="text-align:right; width:120px;">Total Amount</th>
        </tr>
      </thead>
      <tbody>
        ${(normalizedItems || [])
          .map((it) => {
            const lineTotal = (it.unitAmount || 0) * (it.quantity || 0);
            return `<tr>
              <td>${frappe.utils.escape_html(it.description || '')}</td>
              <td style="text-align:center;">${formatNumber(it.quantity || 0)}</td>
              <td style=\"text-align:right;\">${formatNumber(it.unitAmount || 0)}</td>
              <td style=\"text-align:right;\">${formatNumber(lineTotal)}</td>
            </tr>`;
          })
          .join('')}
      </tbody>
    </table>
    <div class="vfd-totals">
      <div class="vfd-totals-inner">
        <div class="vfd-totals-row border" style="padding-top:8px;">
          <span>Total Excl of Tax:</span><span>${formatNumber(totalExcl)}</span>
        </div>
        <div class="vfd-totals-row">
          <span>Tax (18%):</span><span>${formatNumber(taxAmount)}</span>
        </div>
        <div class="vfd-totals-row emph">
          <span>Total Incl of Tax:</span><span>${formatNumber(totalIncl)}</span>
        </div>
      </div>
    </div>
    <div class="vfd-footer">Please verify the above details before sending to TRA.</div>
  </div>`;
  
  let method = ''
  if (vfd_provider === "VFDPlus") {
    method = "csf_tz.vfd_providers.doctype.vfdplus_settings.vfdplus_settings.post_fiscal_receipt"
  } else if (vfd_provider === "TotalVFD") {
    method = "csf_tz.vfd_providers.doctype.total_vfd_setting.total_vfd_setting.post_fiscal_receipt"
  } else if (vfd_provider === "SimplifyVFD") {
    method = "csf_tz.vfd_providers.doctype.simplify_vfd_settings.simplify_vfd_settings.post_fiscal_receipt"
  }

  let d = new frappe.ui.Dialog({
    title: __("VFD Receipt Preview"),
    fields: [
      {
        fieldtype: "HTML",
        fieldname: "preview_html",
        options: receiptHTML,
      },
    ],
    primary_action_label: __("Send To TRA"),
    primary_action() {
      // Submit to TRA
      frappe
        .call({
          method: method,
          args: {
            method: "POST",
            payload: payload,
            invoice_id: frm.doc.name
          },
          freeze: true,
          freeze_message: __("Sending to TRA..."),
        })
        .then((res) => {
            d.hide();
            frm.reload_doc();
            if (res.message.data) {
              frappe.show_alert({
                message: __("VFD successfully sent to TRA"),
                indicator: "green",
              });
            } else {
              frappe.show_alert({
                message: __("VFD sending completed with errors"),
                indicator: "orange",
              });
            }
        })
    },
    secondary_action_label: __("Close"),
    secondary_action() {
      d.hide();
    },
  });

  d.$wrapper.find(".modal-content").css("width", "650px");

  d.show();
}


    // <div class="vfd-center vfd-header">
    //   <p class="vfd-receipt-banner">*** START OF LEGAL RECEIPT ***</p>
    // </div>
        // <div style="font-weight:600; margin-bottom:4px; text-align:center;">CUSTOMER</div>

        // <div style="font-weight:600; margin-bottom:4px; text-align:center;">INVOICE</div>
    
