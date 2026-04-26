# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe

from goods_transport.services.tenant import get_user_tenant_name, is_global_user


def _escape(value: str) -> str:
	return frappe.db.escape(value)


def _tenant_condition(doctype: str, user=None) -> str:
	if is_global_user(user):
		return ""

	tenant_name = get_user_tenant_name(user=user, required=False)
	if not tenant_name:
		return "1=0"

	return f"`tab{doctype}`.`tenant` = {_escape(tenant_name)}"


def _transport_tenant_condition(user=None) -> str:
	if is_global_user(user):
		return ""

	tenant_name = get_user_tenant_name(user=user, required=False)
	if not tenant_name:
		return "1=0"

	return f"`tabTransport Tenant`.`name` = {_escape(tenant_name)}"


def _doc_name(doc):
	return doc if isinstance(doc, str) else getattr(doc, "name", None)


def _tenant_has_permission(doctype: str, doc, user=None) -> bool:
	if is_global_user(user):
		return True

	doc_name = _doc_name(doc)
	if not doc_name:
		return False

	user_tenant = get_user_tenant_name(user=user, required=False)
	if not user_tenant:
		return False

	doc_tenant = frappe.db.get_value(doctype, doc_name, "tenant")
	return doc_tenant == user_tenant


def _transport_tenant_has_permission(doc, user=None) -> bool:
	if is_global_user(user):
		return True

	doc_name = _doc_name(doc)
	user_tenant = get_user_tenant_name(user=user, required=False)
	return bool(doc_name and user_tenant and doc_name == user_tenant)


def get_transport_tenant_query(user=None):
	return _transport_tenant_condition(user=user)


def get_tenant_branch_query(user=None):
	return _tenant_condition("Tenant Branch", user=user)


def get_tenant_user_profile_query(user=None):
	return _tenant_condition("Tenant User Profile", user=user)


def get_commodity_customer_query(user=None):
	return _tenant_condition("Commodity Customer", user=user)


def get_vehicle_owner_query(user=None):
	return _tenant_condition("Vehicle Owner", user=user)


def get_transport_driver_query(user=None):
	return _tenant_condition("Transport Driver", user=user)


def get_transport_vehicle_query(user=None):
	return _tenant_condition("Transport Vehicle", user=user)


def get_transport_load_query(user=None):
	return _tenant_condition("Transport Load", user=user)


def get_tenant_print_setting_query(user=None):
	return _tenant_condition("Tenant Print Setting", user=user)


def get_tenant_whatsapp_setting_query(user=None):
	return _tenant_condition("Tenant WhatsApp Setting", user=user)


def get_tenant_google_map_setting_query(user=None):
	return _tenant_condition("Tenant Google Map Setting", user=user)


def has_transport_tenant_permission(doc, user=None, permission_type=None):
	return _transport_tenant_has_permission(doc, user=user)


def has_tenant_branch_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Tenant Branch", doc, user=user)


def has_tenant_user_profile_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Tenant User Profile", doc, user=user)


def has_commodity_customer_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Commodity Customer", doc, user=user)


def has_vehicle_owner_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Vehicle Owner", doc, user=user)


def has_transport_driver_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Transport Driver", doc, user=user)


def has_transport_vehicle_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Transport Vehicle", doc, user=user)


def has_transport_load_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Transport Load", doc, user=user)


def has_tenant_print_setting_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Tenant Print Setting", doc, user=user)


def has_tenant_whatsapp_setting_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Tenant WhatsApp Setting", doc, user=user)


def has_tenant_google_map_setting_permission(doc, user=None, permission_type=None):
	return _tenant_has_permission("Tenant Google Map Setting", doc, user=user)
