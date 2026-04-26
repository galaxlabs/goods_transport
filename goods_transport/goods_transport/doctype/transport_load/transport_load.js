// Copyright (c) 2026, Galaxy Labs and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Load", {
	refresh(frm) {
		frm.add_custom_button(__("Add Bilty Row"), () => {
			frm.add_child("bilties", {
				payment_type: "Receiver Pay",
				destination_city: frm.doc.destination_city,
			});
			frm.refresh_field("bilties");
		});

		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Invoice Customer"), () => {
				const row = (frm.doc.bilties || []).find((item) => item.invoice_customer);
				if (row) {
					frappe.set_route("Form", "Commodity Customer", row.invoice_customer);
				}
			});
		}
	},
});

