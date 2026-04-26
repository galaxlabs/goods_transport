# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe

from goods_transport.services.tenant import get_current_user_profile_doc, get_user_tenant_doc


def _serialize_profile(profile):
	return {
		"name": profile.name,
		"tenant": profile.tenant,
		"user": profile.user,
		"role_type": profile.role_type,
		"branch": profile.branch,
		"linked_customer": profile.linked_customer,
		"linked_driver": profile.linked_driver,
		"linked_vehicle_owner": profile.linked_vehicle_owner,
		"is_active": profile.is_active,
	}


def _serialize_tenant(tenant):
	return {
		"name": tenant.name,
		"tenant_name": tenant.tenant_name,
		"company_type": tenant.company_type,
		"registration_type": tenant.registration_type,
		"status": tenant.status,
		"default_currency": tenant.default_currency,
	}


@frappe.whitelist()
def get_current_user_profile():
	"""Return the active tenant user profile for the session user."""
	profile = get_current_user_profile_doc(required=True)
	return _serialize_profile(profile)


@frappe.whitelist()
def get_user_tenant():
	"""Return the tenant summary resolved from the active session user."""
	tenant = get_user_tenant_doc(required=True)
	return _serialize_tenant(tenant)
