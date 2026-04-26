# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import cint


GLOBAL_ROLES = {"System Manager", "SaaS Owner"}


def get_session_user(user=None) -> str:
	return user or frappe.session.user


def is_global_user(user=None) -> bool:
	session_user = get_session_user(user)
	if session_user in {"Administrator", "Guest"}:
		return session_user == "Administrator"
	return bool(GLOBAL_ROLES.intersection(set(frappe.get_roles(session_user))))


def get_current_user_profile_doc(user=None, required=False):
	session_user = get_session_user(user)
	profile_name = frappe.db.get_value(
		"Tenant User Profile",
		{"user": session_user, "is_active": 1},
		"name",
		order_by="creation desc",
	)
	if not profile_name:
		if required:
			frappe.throw(_("No active tenant profile is configured for user {0}.").format(session_user))
		return None
	return frappe.get_doc("Tenant User Profile", profile_name)


def get_user_tenant_name(user=None, required=False):
	if is_global_user(user):
		return None

	profile = get_current_user_profile_doc(user=user, required=required)
	if not profile:
		return None
	return profile.tenant


def get_user_tenant_doc(user=None, required=False):
	tenant_name = get_user_tenant_name(user=user, required=required)
	if not tenant_name:
		return None
	return frappe.get_doc("Transport Tenant", tenant_name)


def apply_default_tenant(doc):
	if getattr(doc, "tenant", None):
		return

	tenant_name = get_user_tenant_name(required=False)
	if tenant_name:
		doc.tenant = tenant_name


def validate_tenant_reference(doc):
	tenant_name = getattr(doc, "tenant", None)
	if not tenant_name:
		frappe.throw(_("Tenant is required for {0}.").format(doc.doctype))

	if not frappe.db.exists("Transport Tenant", tenant_name):
		frappe.throw(_("Transport Tenant {0} does not exist.").format(tenant_name))


def validate_same_tenant(linked_doctype: str, linked_name: str, tenant_name: str, label: str):
	if not linked_name:
		return

	linked_tenant = frappe.db.get_value(linked_doctype, linked_name, "tenant")
	if linked_tenant and linked_tenant != tenant_name:
		frappe.throw(_("{0} must belong to tenant {1}.").format(label, tenant_name))


def as_check(value) -> int:
	return cint(value)
