# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe.utils import cint

from goods_transport.services.settings import (
	get_single_tenant_setting,
	resolve_tenant_for_settings,
	serialize_doc,
	update_default_print_setting,
	upsert_single_tenant_setting,
)


@frappe.whitelist()
def get_whatsapp_settings(tenant=None):
	tenant_name = resolve_tenant_for_settings(tenant=tenant)
	doc = get_single_tenant_setting("Tenant WhatsApp Setting", tenant_name)
	if not doc:
		return {"tenant": tenant_name, "provider": "Twilio", "enabled": 0, "sandbox_mode": 0}
	return serialize_doc(doc, hidden_fields={"auth_token_password"})


@frappe.whitelist()
def update_whatsapp_settings(
	tenant=None,
	provider="Twilio",
	account_sid=None,
	auth_token_password=None,
	from_whatsapp_number=None,
	enabled=0,
	sandbox_mode=0,
):
	tenant_name = resolve_tenant_for_settings(tenant=tenant)
	doc = upsert_single_tenant_setting(
		"Tenant WhatsApp Setting",
		tenant_name,
		{
			"provider": provider or "Twilio",
			"account_sid": account_sid,
			"auth_token_password": auth_token_password,
			"from_whatsapp_number": from_whatsapp_number,
			"enabled": cint(enabled),
			"sandbox_mode": cint(sandbox_mode),
		},
	)
	return serialize_doc(doc, hidden_fields={"auth_token_password"})


@frappe.whitelist()
def get_map_settings(tenant=None):
	tenant_name = resolve_tenant_for_settings(tenant=tenant)
	doc = get_single_tenant_setting("Tenant Google Map Setting", tenant_name)
	if not doc:
		return {
			"tenant": tenant_name,
			"enabled": 0,
			"distance_calculation_enabled": 0,
			"route_preview_enabled": 0,
			"live_tracking_enabled": 0,
		}
	return serialize_doc(doc, hidden_fields={"google_api_key_password"})


@frappe.whitelist()
def update_map_settings(
	tenant=None,
	google_api_key_password=None,
	enabled=0,
	distance_calculation_enabled=0,
	route_preview_enabled=0,
	live_tracking_enabled=0,
):
	tenant_name = resolve_tenant_for_settings(tenant=tenant)
	doc = upsert_single_tenant_setting(
		"Tenant Google Map Setting",
		tenant_name,
		{
			"google_api_key_password": google_api_key_password,
			"enabled": cint(enabled),
			"distance_calculation_enabled": cint(distance_calculation_enabled),
			"route_preview_enabled": cint(route_preview_enabled),
			"live_tracking_enabled": cint(live_tracking_enabled),
		},
	)
	return serialize_doc(doc, hidden_fields={"google_api_key_password"})


@frappe.whitelist()
def get_tenant_print_settings(tenant=None, print_type=None):
	tenant_name = resolve_tenant_for_settings(tenant=tenant)
	filters = {"tenant": tenant_name}
	if print_type:
		filters["print_type"] = print_type

	return [
		serialize_doc(doc)
		for doc in frappe.get_all(
			"Tenant Print Setting",
			filters=filters,
			fields=["name"],
			order_by="print_type asc, is_default desc, modified desc",
		)
		for doc in [frappe.get_doc("Tenant Print Setting", doc.name)]
	]


@frappe.whitelist()
def update_tenant_print_settings(
	tenant=None,
	name=None,
	print_type=None,
	title=None,
	letterhead=None,
	header_html=None,
	footer_html=None,
	terms_and_conditions=None,
	language="English",
	signature_image=None,
	stamp_image=None,
	is_default=0,
):
	tenant_name = resolve_tenant_for_settings(tenant=tenant)
	if name:
		doc = frappe.get_doc("Tenant Print Setting", name)
		if doc.tenant != tenant_name:
			frappe.throw("Print setting does not belong to your tenant.")
	else:
		doc = frappe.new_doc("Tenant Print Setting")
		doc.tenant = tenant_name

	for fieldname, value in {
		"print_type": print_type,
		"title": title,
		"letterhead": letterhead,
		"header_html": header_html,
		"footer_html": footer_html,
		"terms_and_conditions": terms_and_conditions,
		"language": language,
		"signature_image": signature_image,
		"stamp_image": stamp_image,
		"is_default": cint(is_default),
	}.items():
		if value is not None:
			doc.set(fieldname, value)

	doc.save(ignore_permissions=True)
	update_default_print_setting(doc)
	return serialize_doc(doc)
