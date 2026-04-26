# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe

from goods_transport.services.onboarding import (
	create_customer,
	create_driver,
	create_transport_company,
	create_transport_load,
	create_vehicle,
	create_vehicle_owner,
	ensure_tenant_user_profile,
	ensure_user,
	serialize_doc,
)
from goods_transport.services.erpnext_sync import sync_commodity_customer


@frappe.whitelist(allow_guest=True)
def register_transport_company(**kwargs):
	tenant, admin, profile = create_transport_company(kwargs)
	return {
		"tenant": tenant.name,
		"tenant_name": tenant.tenant_name,
		"admin_user": admin.name,
		"profile": serialize_doc(profile, fields=["tenant", "user", "role_type", "is_active"]),
	}


@frappe.whitelist()
def register_customer(**kwargs):
	doc = create_customer(kwargs, tenant=kwargs.get("tenant"))
	if kwargs.get("portal_user_email"):
		user = ensure_user(kwargs.get("portal_user_email"), kwargs.get("customer_name"), kwargs.get("portal_password"), ["Customer"])
		doc.portal_user = user.name
		doc.save(ignore_permissions=True)
		ensure_tenant_user_profile(doc.tenant, user.name, "Customer", linked_customer=doc.name)
	return serialize_doc(doc)


@frappe.whitelist()
def sync_customer_to_erpnext(customer):
	doc = frappe.get_doc("Commodity Customer", customer)
	result = sync_commodity_customer(doc)
	return {"commodity_customer": doc.name, **result}


@frappe.whitelist()
def register_vehicle_owner(**kwargs):
	doc = create_vehicle_owner(kwargs, tenant=kwargs.get("tenant"))
	if kwargs.get("portal_user_email"):
		user = ensure_user(kwargs.get("portal_user_email"), kwargs.get("owner_name"), kwargs.get("portal_password"), ["Vehicle Owner"])
		doc.portal_user = user.name
		doc.save(ignore_permissions=True)
		ensure_tenant_user_profile(doc.tenant, user.name, "Vehicle Owner", linked_vehicle_owner=doc.name)
	return serialize_doc(doc)


@frappe.whitelist()
def register_driver(**kwargs):
	doc = create_driver(kwargs, tenant=kwargs.get("tenant"))
	if kwargs.get("portal_user_email"):
		user = ensure_user(kwargs.get("portal_user_email"), kwargs.get("driver_name"), kwargs.get("portal_password"), ["Driver"])
		doc.portal_user = user.name
		doc.save(ignore_permissions=True)
		ensure_tenant_user_profile(
			doc.tenant,
			user.name,
			"Driver",
			linked_driver=doc.name,
			linked_vehicle_owner=doc.linked_vehicle_owner,
		)
	return serialize_doc(doc)


@frappe.whitelist()
def register_vehicle(**kwargs):
	doc = create_vehicle(kwargs, tenant=kwargs.get("tenant"))
	return serialize_doc(doc)


@frappe.whitelist()
def register_local_load(**kwargs):
	doc = create_transport_load(kwargs, tenant=kwargs.get("tenant"))
	return serialize_doc(
		doc,
		fields=[
			"tenant",
			"posting_date",
			"load_type",
			"origin_city",
			"destination_city",
			"vehicle",
			"driver",
			"vehicle_owner",
			"status",
			"total_bilties",
			"total_freight",
			"paid_amount",
			"receiver_pay_amount",
		],
	)
