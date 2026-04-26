# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import cint

from goods_transport.services.erpnext_sync import erpnext_customer_sync_available, sync_commodity_customer
from goods_transport.services.tenant import get_current_user_profile_doc, is_global_user, validate_same_tenant


TENANT_MANAGER_ROLES = {"Tenant Admin", "Transport Manager"}


def tenant_for_onboarding(tenant=None):
	if is_global_user():
		return tenant

	profile = get_current_user_profile_doc(required=True)
	if profile.role_type not in TENANT_MANAGER_ROLES:
		frappe.throw(_("You are not allowed to register tenant records."))
	return profile.tenant


def require_tenant(tenant=None):
	tenant_name = tenant_for_onboarding(tenant=tenant)
	if not tenant_name:
		frappe.throw(_("Tenant is required."))
	return tenant_name


def serialize_doc(doc, fields=None):
	fields = fields or [field.fieldname for field in frappe.get_meta(doc.doctype).fields]
	data = {"doctype": doc.doctype, "name": doc.name}
	for fieldname in fields:
		data[fieldname] = doc.get(fieldname)
	return data


def ensure_user(email: str, first_name: str, password=None, roles=None):
	if not email:
		frappe.throw(_("Email is required."))

	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name or email.split("@")[0],
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
				"new_password": password,
			}
		).insert(ignore_permissions=True)

	for role in roles or []:
		if not any(row.role == role for row in user.roles):
			user.append("roles", {"role": role})

	user.save(ignore_permissions=True)
	return user


def ensure_tenant_user_profile(
	tenant: str,
	user: str,
	role_type: str,
	branch=None,
	linked_customer=None,
	linked_driver=None,
	linked_vehicle_owner=None,
):
	existing = frappe.db.get_value("Tenant User Profile", {"user": user}, "name")
	if existing:
		profile = frappe.get_doc("Tenant User Profile", existing)
		if profile.tenant != tenant:
			frappe.throw(_("User already belongs to another tenant."))
	else:
		profile = frappe.new_doc("Tenant User Profile")
		profile.tenant = tenant
		profile.user = user

	profile.role_type = role_type
	profile.branch = branch
	profile.linked_customer = linked_customer
	profile.linked_driver = linked_driver
	profile.linked_vehicle_owner = linked_vehicle_owner
	profile.is_active = 1
	profile.save(ignore_permissions=True)
	return profile


def create_transport_company(data):
	tenant = frappe.get_doc(
		{
			"doctype": "Transport Tenant",
			"tenant_name": data["tenant_name"],
			"company_type": data.get("company_type") or "Transport",
			"registration_type": data.get("registration_type") or "Company",
			"ntn": data.get("ntn"),
			"strn": data.get("strn"),
			"cnic": data.get("cnic"),
			"phone": data.get("phone"),
			"whatsapp_number": data.get("whatsapp_number"),
			"email": data.get("email") or data.get("admin_email"),
			"address": data.get("address"),
			"city": data.get("city"),
			"province": data.get("province"),
			"status": data.get("status") or "Trial",
			"default_currency": data.get("default_currency") or "PKR",
			"subscription_plan": data.get("subscription_plan"),
		}
	).insert(ignore_permissions=True)

	admin = ensure_user(
		data.get("admin_email"),
		data.get("admin_first_name") or data.get("tenant_name"),
		password=data.get("admin_password"),
		roles=["Tenant Admin"],
	)
	profile = ensure_tenant_user_profile(tenant.name, admin.name, "Tenant Admin")
	return tenant, admin, profile


def create_customer(data, tenant=None):
	tenant_name = require_tenant(tenant=tenant)
	doc = frappe.get_doc(
		{
			"doctype": "Commodity Customer",
			"tenant": tenant_name,
			"customer_name": data["customer_name"],
			"business_name": data.get("business_name"),
			"customer_type": data.get("customer_type") or "Individual",
			"cnic": data.get("cnic"),
			"ntn": data.get("ntn"),
			"strn": data.get("strn"),
			"mobile": data.get("mobile"),
			"whatsapp": data.get("whatsapp"),
			"email": data.get("email"),
			"city": data.get("city"),
			"address": data.get("address"),
			"credit_limit": data.get("credit_limit"),
			"payment_terms": data.get("payment_terms"),
			"opening_balance": data.get("opening_balance"),
			"portal_user": data.get("portal_user"),
			"erpnext_customer": data.get("erpnext_customer"),
			"erpnext_contact": data.get("erpnext_contact"),
			"erpnext_address": data.get("erpnext_address"),
			"status": data.get("status") or "Active",
		}
	).insert(ignore_permissions=True)
	if cint(data.get("sync_to_erpnext", 1)) and erpnext_customer_sync_available():
		sync_commodity_customer(doc)
	return doc


def _normalize_rows(data, key):
	rows = data.get(key) or []
	if isinstance(rows, str):
		rows = frappe.parse_json(rows)
	return rows or []


def _find_customer_by_party(tenant_name, party):
	filters = {"tenant": tenant_name, "customer_name": party.get("customer_name")}
	if party.get("mobile"):
		filters["mobile"] = party.get("mobile")
	if party.get("email"):
		filters["email"] = party.get("email")
	return frappe.db.get_value("Commodity Customer", filters, "name")


def ensure_commodity_customer_for_party(tenant_name, party):
	if party.get("customer"):
		validate_same_tenant("Commodity Customer", party.get("customer"), tenant_name, party.get("label") or "Customer")
		customer = frappe.get_doc("Commodity Customer", party.get("customer"))
		if cint(party.get("sync_to_erpnext", 1)) and not customer.erpnext_customer and erpnext_customer_sync_available():
			sync_commodity_customer(customer)
		return customer

	if not party.get("customer_name"):
		return None

	existing = _find_customer_by_party(tenant_name, party)
	if existing:
		customer = frappe.get_doc("Commodity Customer", existing)
	else:
		customer = create_customer(
			{
				"customer_name": party.get("customer_name"),
				"customer_type": party.get("customer_type") or "Individual",
				"mobile": party.get("mobile"),
				"whatsapp": party.get("whatsapp"),
				"email": party.get("email"),
				"city": party.get("city"),
				"address": party.get("address"),
				"sync_to_erpnext": party.get("sync_to_erpnext", 1),
			},
			tenant=tenant_name,
		)
	return customer


def _party_from_bilty(row, prefix, label):
	return {
		"label": label,
		"customer": row.get(f"{prefix}_customer"),
		"customer_name": row.get(f"{prefix}_name"),
		"customer_type": row.get(f"{prefix}_customer_type") or "Individual",
		"mobile": row.get(f"{prefix}_mobile"),
		"whatsapp": row.get(f"{prefix}_whatsapp"),
		"email": row.get(f"{prefix}_email"),
		"city": row.get(f"{prefix}_city") or row.get("destination_city"),
		"address": row.get(f"{prefix}_address"),
		"sync_to_erpnext": row.get("sync_parties_to_erpnext", 1),
	}


def create_transport_load(data, tenant=None):
	tenant_name = require_tenant(tenant=tenant)
	validate_same_tenant("Transport Vehicle", data.get("vehicle"), tenant_name, "Vehicle")
	validate_same_tenant("Transport Driver", data.get("driver"), tenant_name, "Driver")
	validate_same_tenant("Vehicle Owner", data.get("vehicle_owner"), tenant_name, "Vehicle Owner")

	load = frappe.get_doc(
		{
			"doctype": "Transport Load",
			"tenant": tenant_name,
			"posting_date": data.get("posting_date") or frappe.utils.today(),
			"load_type": data.get("load_type") or "Local",
			"origin_city": data.get("origin_city"),
			"destination_city": data.get("destination_city"),
			"vehicle": data.get("vehicle"),
			"driver": data.get("driver"),
			"vehicle_owner": data.get("vehicle_owner"),
			"status": data.get("status") or "Draft",
			"remarks": data.get("remarks"),
		}
	)

	for row in _normalize_rows(data, "bilties"):
		sender = ensure_commodity_customer_for_party(tenant_name, _party_from_bilty(row, "sender", "Sender"))
		receiver = ensure_commodity_customer_for_party(tenant_name, _party_from_bilty(row, "receiver", "Receiver"))
		invoice_customer = row.get("invoice_customer")
		if not invoice_customer:
			invoice_customer = sender.name if row.get("payment_type") == "Paid" and sender else receiver.name if receiver else None
		validate_same_tenant("Commodity Customer", invoice_customer, tenant_name, "Invoice Customer")

		load.append(
			"bilties",
			{
				"bilty_no": row.get("bilty_no"),
				"sender_customer": sender.name if sender else None,
				"sender_name": row.get("sender_name") or (sender.customer_name if sender else None),
				"sender_mobile": row.get("sender_mobile"),
				"sender_address": row.get("sender_address"),
				"receiver_customer": receiver.name if receiver else None,
				"receiver_name": row.get("receiver_name") or (receiver.customer_name if receiver else None),
				"receiver_mobile": row.get("receiver_mobile"),
				"receiver_address": row.get("receiver_address"),
				"destination_city": row.get("destination_city") or data.get("destination_city"),
				"goods_description": row.get("goods_description"),
				"packages": row.get("packages"),
				"weight": row.get("weight"),
				"freight_amount": row.get("freight_amount"),
				"payment_type": row.get("payment_type") or "Receiver Pay",
				"invoice_customer": invoice_customer,
			},
		)

	load.insert(ignore_permissions=True)
	return load


def create_vehicle_owner(data, tenant=None):
	tenant_name = require_tenant(tenant=tenant)
	doc = frappe.get_doc(
		{
			"doctype": "Vehicle Owner",
			"tenant": tenant_name,
			"owner_name": data["owner_name"],
			"registration_type": data.get("registration_type") or "Individual",
			"cnic": data.get("cnic"),
			"ntn": data.get("ntn"),
			"mobile": data.get("mobile"),
			"whatsapp": data.get("whatsapp"),
			"address": data.get("address"),
			"bank_name": data.get("bank_name"),
			"account_title": data.get("account_title"),
			"account_number": data.get("account_number"),
			"iban": data.get("iban"),
			"portal_user": data.get("portal_user"),
			"can_drive_self": cint(data.get("can_drive_self")),
			"status": data.get("status") or "Active",
		}
	).insert(ignore_permissions=True)
	return doc


def create_driver(data, tenant=None):
	tenant_name = require_tenant(tenant=tenant)
	validate_same_tenant("Vehicle Owner", data.get("linked_vehicle_owner"), tenant_name, "Linked Vehicle Owner")
	doc = frappe.get_doc(
		{
			"doctype": "Transport Driver",
			"tenant": tenant_name,
			"driver_name": data["driver_name"],
			"cnic": data.get("cnic"),
			"mobile": data.get("mobile"),
			"whatsapp": data.get("whatsapp"),
			"license_number": data.get("license_number"),
			"license_expiry": data.get("license_expiry"),
			"emergency_contact": data.get("emergency_contact"),
			"portal_user": data.get("portal_user"),
			"can_register_own_vehicle": cint(data.get("can_register_own_vehicle")),
			"linked_vehicle_owner": data.get("linked_vehicle_owner"),
			"status": data.get("status") or "Active",
		}
	).insert(ignore_permissions=True)
	return doc


def create_vehicle(data, tenant=None):
	tenant_name = require_tenant(tenant=tenant)
	validate_same_tenant("Vehicle Owner", data.get("vehicle_owner"), tenant_name, "Owner")
	validate_same_tenant("Transport Driver", data.get("driver"), tenant_name, "Driver")
	doc = frappe.get_doc(
		{
			"doctype": "Transport Vehicle",
			"tenant": tenant_name,
			"vehicle_number": data["vehicle_number"],
			"vehicle_type": data.get("vehicle_type") or "Truck",
			"vehicle_owner": data["vehicle_owner"],
			"driver": data.get("driver"),
			"capacity_weight": data.get("capacity_weight"),
			"capacity_weight_unit": data.get("capacity_weight_unit"),
			"capacity_volume": data.get("capacity_volume"),
			"registration_book_image": data.get("registration_book_image"),
			"fitness_certificate": data.get("fitness_certificate"),
			"route_permit": data.get("route_permit"),
			"insurance_expiry": data.get("insurance_expiry"),
			"status": data.get("status") or "Available",
		}
	).insert(ignore_permissions=True)
	return doc
