# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _


def erpnext_customer_sync_available() -> bool:
	return bool(frappe.db.exists("DocType", "Customer"))


def _first_existing(doctype: str, candidates: list[str], fallback=None):
	for candidate in candidates:
		if candidate and frappe.db.exists(doctype, candidate):
			return candidate
	return fallback


def _default_customer_group():
	return _first_existing(
		"Customer Group",
		["Commercial", "Individual", "All Customer Groups"],
		frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
	)


def _default_territory():
	return _first_existing("Territory", ["Pakistan", "All Territories"], frappe.db.get_value("Territory", {}, "name"))


def _erpnext_customer_type(customer_type: str | None):
	if customer_type == "Individual":
		return "Individual"
	return "Company"


def _split_name(full_name: str):
	parts = (full_name or "").strip().split(maxsplit=1)
	return parts[0] if parts else _("Unknown"), parts[1] if len(parts) > 1 else None


def _find_dynamic_link(parenttype: str, link_doctype: str, link_name: str):
	return frappe.db.get_value(
		"Dynamic Link",
		{"parenttype": parenttype, "link_doctype": link_doctype, "link_name": link_name},
		"parent",
	)


def _ensure_contact(customer_name: str, party_name: str, email=None, mobile=None):
	if not (party_name or email or mobile):
		return None

	contact_name = _find_dynamic_link("Contact", "Customer", customer_name)
	if contact_name:
		contact = frappe.get_doc("Contact", contact_name)
	else:
		first_name, last_name = _split_name(party_name)
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": first_name,
				"last_name": last_name,
				"is_primary_contact": 1,
			}
		)
		contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	if email and not any(row.email_id == email for row in contact.email_ids):
		contact.append("email_ids", {"email_id": email, "is_primary": 1})
	if mobile and not any(row.phone == mobile for row in contact.phone_nos):
		contact.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})

	contact.save(ignore_permissions=True)
	return contact


def _ensure_address(customer_name: str, party_name: str, address=None, city=None, email=None, mobile=None):
	if not (address or city):
		return None

	address_name = _find_dynamic_link("Address", "Customer", customer_name)
	if address_name:
		address_doc = frappe.get_doc("Address", address_name)
	else:
		address_doc = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": party_name or customer_name,
				"address_type": "Billing",
				"address_line1": address or city or party_name or customer_name,
				"city": city or "Unknown",
				"country": "Pakistan",
				"is_primary_address": 1,
				"is_shipping_address": 1,
			}
		)
		address_doc.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	address_doc.email_id = email
	address_doc.phone = mobile
	address_doc.save(ignore_permissions=True)
	return address_doc


def ensure_erpnext_customer(commodity_customer):
	if not erpnext_customer_sync_available():
		return None

	customer_name = commodity_customer.get("erpnext_customer") or frappe.db.get_value(
		"Customer",
		{"customer_name": commodity_customer.customer_name},
		"name",
	)

	if customer_name:
		customer = frappe.get_doc("Customer", customer_name)
	else:
		customer = frappe.new_doc("Customer")

	customer.customer_name = commodity_customer.customer_name
	customer.customer_type = _erpnext_customer_type(commodity_customer.customer_type)
	customer.customer_group = customer.customer_group or _default_customer_group()
	customer.territory = customer.territory or _default_territory()
	customer.mobile_no = commodity_customer.mobile
	customer.email_id = commodity_customer.email
	customer.tax_id = commodity_customer.ntn or commodity_customer.cnic
	customer.disabled = 1 if commodity_customer.status == "Inactive" else 0
	customer.save(ignore_permissions=True)

	contact = _ensure_contact(customer.name, commodity_customer.customer_name, commodity_customer.email, commodity_customer.mobile)
	address = _ensure_address(
		customer.name,
		commodity_customer.customer_name,
		commodity_customer.address,
		commodity_customer.city,
		commodity_customer.email,
		commodity_customer.mobile,
	)

	if contact and hasattr(customer, "customer_primary_contact"):
		customer.customer_primary_contact = contact.name
	if address and hasattr(customer, "customer_primary_address"):
		customer.customer_primary_address = address.name
	if (contact or address) and not customer.flags.in_sync_save:
		customer.flags.in_sync_save = True
		customer.save(ignore_permissions=True)

	return {
		"customer": customer.name,
		"contact": contact.name if contact else None,
		"address": address.name if address else None,
	}


def sync_commodity_customer(commodity_customer):
	result = ensure_erpnext_customer(commodity_customer)
	if not result:
		frappe.throw(_("ERPNext Customer DocType is not available on this site."))

	commodity_customer.erpnext_customer = result["customer"]
	commodity_customer.erpnext_contact = result["contact"]
	commodity_customer.erpnext_address = result["address"]
	commodity_customer.synced_to_erpnext = 1
	commodity_customer.save(ignore_permissions=True)
	return result
