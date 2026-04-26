# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import cint

from goods_transport.services.tenant import get_current_user_profile_doc, is_global_user


SETTING_ADMIN_ROLES = {"Tenant Admin", "Transport Manager", "Warehouse Manager"}


def resolve_tenant_for_settings(tenant=None):
	if is_global_user():
		if not tenant:
			frappe.throw(_("Tenant is required for global users."))
		return tenant

	profile = get_current_user_profile_doc(required=True)
	if profile.role_type not in SETTING_ADMIN_ROLES:
		frappe.throw(_("You are not allowed to manage tenant settings."))
	return profile.tenant


def serialize_doc(doc, hidden_fields=None):
	hidden_fields = set(hidden_fields or [])
	data = {"name": doc.name}
	for field in frappe.get_meta(doc.doctype).fields:
		if field.fieldname in hidden_fields:
			continue
		data[field.fieldname] = doc.get(field.fieldname)
	return data


def get_single_tenant_setting(doctype: str, tenant: str):
	name = frappe.db.get_value(doctype, {"tenant": tenant}, "name")
	if not name:
		return None
	return frappe.get_doc(doctype, name)


def upsert_single_tenant_setting(doctype: str, tenant: str, values: dict):
	doc = get_single_tenant_setting(doctype, tenant)
	if not doc:
		doc = frappe.new_doc(doctype)
		doc.tenant = tenant

	for fieldname, value in values.items():
		if value is not None:
			doc.set(fieldname, value)

	doc.save(ignore_permissions=True)
	return doc


def update_default_print_setting(doc):
	if not cint(doc.is_default):
		return

	frappe.db.set_value(
		"Tenant Print Setting",
		{
			"tenant": doc.tenant,
			"print_type": doc.print_type,
			"name": ["!=", doc.name],
		},
		"is_default",
		0,
	)
