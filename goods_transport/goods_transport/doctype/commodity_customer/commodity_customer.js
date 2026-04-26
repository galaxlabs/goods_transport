// Copyright (c) 2026, Galaxy Labs and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commodity Customer", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Sync to ERPNext"), () => {
			frappe.call({
				method: "goods_transport.api.onboarding.sync_customer_to_erpnext",
				args: {
					customer: frm.doc.name,
				},
				freeze: true,
				freeze_message: __("Syncing customer..."),
				callback: (response) => {
					if (!response.exc) {
						frappe.show_alert({
							message: __("ERPNext customer synced"),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		});

		if (frm.doc.erpnext_customer) {
			frm.add_custom_button(__("Open ERPNext Customer"), () => {
				frappe.set_route("Form", "Customer", frm.doc.erpnext_customer);
			});
		}
	},
});
