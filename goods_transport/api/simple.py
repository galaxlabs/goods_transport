# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import cint

from goods_transport.services.onboarding import (
	create_customer as create_commodity_customer,
	create_driver as create_transport_driver,
	create_vehicle as create_transport_vehicle,
	create_vehicle_owner,
	require_tenant,
	tenant_for_onboarding,
)
from goods_transport.services.tenant import validate_same_tenant


RECORD_CONFIG = {
	"customer": {
		"doctype": "Commodity Customer",
		"label_field": "customer_name",
		"editable_fields": {
			"customer_name",
			"business_name",
			"customer_type",
			"mobile",
			"whatsapp",
			"email",
			"city",
			"address",
			"status",
		},
		"aliases": {"label": "customer_name", "customer": "customer_name", "type": "customer_type"},
	},
	"vehicle": {
		"doctype": "Transport Vehicle",
		"label_field": "vehicle_number",
		"editable_fields": {
			"vehicle_number",
			"vehicle_type",
			"status",
			"capacity_weight",
			"capacity_weight_unit",
			"capacity_volume",
			"current_lat",
			"current_lng",
		},
		"aliases": {"label": "vehicle_number", "vehicle": "vehicle_number", "type": "vehicle_type", "lat": "current_lat", "lng": "current_lng"},
	},
	"load": {
		"doctype": "Transport Load",
		"label_field": "name",
		"editable_fields": {
			"posting_date",
			"load_type",
			"origin_city",
			"destination_city",
			"status",
			"remarks",
		},
		"aliases": {"label": "name"},
	},
}


@frappe.whitelist(allow_guest=True)
def connection_status():
	user = frappe.session.user or "Guest"
	authenticated = user != "Guest"
	return {
		"reachable": True,
		"authenticated": authenticated,
		"user": user if authenticated else None,
		"message": f"Backend reachable • Logged in as {user}" if authenticated else "Backend reachable • Guest session",
	}


def _payload(data=None, **kwargs):
	if isinstance(data, str):
		data = frappe.parse_json(data)
	payload = frappe._dict(data or {})
	payload.update({key: value for key, value in kwargs.items() if value is not None})
	return payload


def _first_value(data, *keys):
	for key in keys:
		value = data.get(key)
		if value not in (None, ""):
			return value
	return None


def _customer_payload(doc):
	return {
		"id": doc.name,
		"label": doc.customer_name,
		"customer": doc.name,
		"doctype": doc.doctype,
		"tenant": doc.tenant,
		"erpnext_customer": doc.get("erpnext_customer"),
	}


def _vehicle_payload(doc):
	return {
		"id": doc.name,
		"label": doc.vehicle_number,
		"vehicle": doc.name,
		"doctype": doc.doctype,
		"tenant": doc.tenant,
		"vehicle_owner": doc.vehicle_owner,
		"driver": doc.driver,
	}


def _simple_options(doctype, label_field, search=None, tenant=None, limit=20):
	filters = {}
	tenant_name = tenant_for_onboarding(tenant=tenant)
	if tenant_name:
		filters["tenant"] = tenant_name

	or_filters = None
	if search:
		or_filters = [[doctype, label_field, "like", f"%{search}%"]]

	rows = frappe.get_all(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=["name", label_field],
		limit_page_length=cint(limit) or 20,
		order_by=f"{label_field} asc",
	)
	return [{"id": row.name, "label": row.get(label_field)} for row in rows]


def _tenant_filter(tenant=None):
	tenant_name = tenant_for_onboarding(tenant=tenant)
	return {"tenant": tenant_name} if tenant_name else {}


def _tenant_condition(doctype, tenant=None):
	filters = _tenant_filter(tenant=tenant)
	if not filters:
		return "", {}
	return f"where `tab{doctype}`.`tenant` = %(tenant)s", filters


def _count(doctype, tenant=None, extra_filters=None):
	filters = _tenant_filter(tenant=tenant)
	if extra_filters:
		filters.update(extra_filters)
	return frappe.db.count(doctype, filters)


def _group_counts(doctype, group_field, tenant=None):
	filters = _tenant_filter(tenant=tenant)
	rows = frappe.get_all(
		doctype,
		filters=filters,
		fields=[f"{group_field} as label", "count(name) as value"],
		group_by=group_field,
		order_by="value desc",
	)
	return [{"label": row.label or "Not Set", "value": cint(row.value)} for row in rows]


def _recent_activity(tenant=None):
	where, params = _tenant_condition("Transport Load", tenant=tenant)
	rows = frappe.db.sql(
		f"""
		select
			date_format(posting_date, '%%b %%d') as label,
			count(name) as value,
			coalesce(sum(total_freight), 0) as freight
		from `tabTransport Load`
		{where}
		group by posting_date
		order by posting_date desc
		limit 8
		""",
		params,
		as_dict=True,
	)
	rows.reverse()
	return [
		{"label": row.label, "value": cint(row.value), "freight": float(row.freight or 0)}
		for row in rows
	]


def _record_config(kind):
	config = RECORD_CONFIG.get(kind)
	if not config:
		frappe.throw(_("Unsupported record type {0}.").format(kind))
	return config


def _assert_record_tenant(doctype, name, tenant=None):
	tenant_name = tenant_for_onboarding(tenant=tenant)
	if tenant_name:
		validate_same_tenant(doctype, name, tenant_name, doctype)


def _record_payload(kind, doc):
	config = _record_config(kind)
	data = {
		"kind": kind,
		"doctype": doc.doctype,
		"id": doc.name,
		"label": doc.get(config["label_field"]) if config["label_field"] != "name" else doc.name,
		"tenant": doc.get("tenant"),
		"desk_url": f"/app/{frappe.scrub(doc.doctype).replace('_', '-')}/{doc.name}",
		"fields": {},
	}
	for fieldname in sorted(config["editable_fields"]):
		value = doc.get(fieldname)
		data["fields"][fieldname] = value
		data[fieldname] = value
	return data


def _normalize_update_data(kind, data):
	config = _record_config(kind)
	normalized = {}
	for key, value in data.items():
		fieldname = config["aliases"].get(key, key)
		if fieldname == "name":
			continue
		if fieldname not in config["editable_fields"]:
			continue
		normalized[fieldname] = value
	return normalized


def _ensure_vehicle_owner(tenant_name, data):
	vehicle_owner = _first_value(data, "vehicle_owner", "owner_id")
	if vehicle_owner:
		validate_same_tenant("Vehicle Owner", vehicle_owner, tenant_name, "Vehicle Owner")
		return vehicle_owner

	owner_name = _first_value(data, "owner", "owner_name", "vehicle_owner_name")
	if not owner_name:
		frappe.throw(_("Owner is required to create a vehicle."))

	existing = frappe.db.get_value("Vehicle Owner", {"tenant": tenant_name, "owner_name": owner_name}, "name")
	if existing:
		return existing

	return create_vehicle_owner(
		{
			"owner_name": owner_name,
			"registration_type": data.get("owner_registration_type") or "Individual",
			"mobile": data.get("owner_mobile"),
			"whatsapp": data.get("owner_whatsapp"),
			"address": data.get("owner_address"),
		},
		tenant=tenant_name,
	).name


def _ensure_driver(tenant_name, data, vehicle_owner):
	driver = _first_value(data, "driver", "driver_id")
	if driver and frappe.db.exists("Transport Driver", driver):
		validate_same_tenant("Transport Driver", driver, tenant_name, "Driver")
		return driver

	driver_name = _first_value(data, "driver_name")
	if not driver_name and driver and not frappe.db.exists("Transport Driver", driver):
		driver_name = driver
	if not driver_name:
		return None

	existing = frappe.db.get_value("Transport Driver", {"tenant": tenant_name, "driver_name": driver_name}, "name")
	if existing:
		return existing

	return create_transport_driver(
		{
			"driver_name": driver_name,
			"mobile": data.get("driver_mobile"),
			"whatsapp": data.get("driver_whatsapp"),
			"linked_vehicle_owner": vehicle_owner,
		},
		tenant=tenant_name,
	).name


@frappe.whitelist()
def create_customer(data=None, **kwargs):
	data = _payload(data, **kwargs)
	customer_name = _first_value(data, "customer", "label", "customer_name", "name")
	if not customer_name:
		frappe.throw(_("Customer is required."))

	doc = create_commodity_customer(
		{
			"customer_name": customer_name,
			"business_name": data.get("business_name"),
			"customer_type": data.get("customer_type") or "Individual",
			"mobile": data.get("mobile"),
			"whatsapp": data.get("whatsapp"),
			"email": data.get("email"),
			"city": data.get("city"),
			"address": data.get("address"),
			"sync_to_erpnext": data.get("sync_to_erpnext", 1),
		},
		tenant=data.get("tenant"),
	)
	return _customer_payload(doc)


@frappe.whitelist()
def create_vehicle(data=None, **kwargs):
	data = _payload(data, **kwargs)
	vehicle_number = _first_value(data, "vehicle", "label", "vehicle_number", "name")
	if not vehicle_number:
		frappe.throw(_("Vehicle is required."))

	tenant_name = require_tenant(data.get("tenant"))
	vehicle_owner = _ensure_vehicle_owner(tenant_name, data)
	driver = _ensure_driver(tenant_name, data, vehicle_owner)
	doc = create_transport_vehicle(
		{
			"vehicle_number": vehicle_number,
			"vehicle_type": data.get("vehicle_type") or "Truck",
			"vehicle_owner": vehicle_owner,
			"driver": driver,
			"capacity_weight": data.get("capacity_weight"),
			"capacity_weight_unit": data.get("capacity_weight_unit"),
			"capacity_volume": data.get("capacity_volume"),
			"status": data.get("status") or "Available",
		},
		tenant=tenant_name,
	)
	return _vehicle_payload(doc)


@frappe.whitelist()
def get_customers(search=None, tenant=None, limit=20):
	return _simple_options("Commodity Customer", "customer_name", search=search, tenant=tenant, limit=limit)


@frappe.whitelist()
def get_vehicles(search=None, tenant=None, limit=20):
	return _simple_options("Transport Vehicle", "vehicle_number", search=search, tenant=tenant, limit=limit)


@frappe.whitelist()
def get_dashboard(tenant=None):
	return {
		"stats": {
			"customers": _count("Commodity Customer", tenant=tenant),
			"vehicles": _count("Transport Vehicle", tenant=tenant),
			"loads": _count("Transport Load", tenant=tenant),
			"available_vehicles": _count("Transport Vehicle", tenant=tenant, extra_filters={"status": "Available"}),
		},
		"charts": {
			"vehicle_status": _group_counts("Transport Vehicle", "status", tenant=tenant),
			"customer_type": _group_counts("Commodity Customer", "customer_type", tenant=tenant),
			"load_status": _group_counts("Transport Load", "status", tenant=tenant),
			"recent_loads": _recent_activity(tenant=tenant),
		},
	}


@frappe.whitelist()
def list_customers(search=None, tenant=None, limit=50):
	filters = _tenant_filter(tenant=tenant)
	or_filters = [["Commodity Customer", "customer_name", "like", f"%{search}%"]] if search else None
	rows = frappe.get_all(
		"Commodity Customer",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "customer_name", "customer_type", "mobile", "city", "status", "erpnext_customer"],
		limit_page_length=cint(limit) or 50,
		order_by="modified desc",
	)
	return {
		"rows": [
			{
				"id": row.name,
				"label": row.customer_name,
				"type": row.customer_type,
				"mobile": row.mobile,
				"city": row.city,
				"status": row.status,
				"erpnext_customer": row.erpnext_customer,
			}
			for row in rows
		]
	}


@frappe.whitelist()
def list_vehicles(search=None, tenant=None, limit=50):
	filters = _tenant_filter(tenant=tenant)
	or_filters = [["Transport Vehicle", "vehicle_number", "like", f"%{search}%"]] if search else None
	rows = frappe.get_all(
		"Transport Vehicle",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"vehicle_number",
			"vehicle_type",
			"vehicle_owner",
			"driver",
			"status",
			"current_lat",
			"current_lng",
		],
		limit_page_length=cint(limit) or 50,
		order_by="modified desc",
	)
	return {
		"rows": [
			{
				"id": row.name,
				"label": row.vehicle_number,
				"type": row.vehicle_type,
				"owner": row.vehicle_owner,
				"driver": row.driver,
				"status": row.status,
				"lat": row.current_lat,
				"lng": row.current_lng,
			}
			for row in rows
		]
	}


@frappe.whitelist()
def list_loads(search=None, tenant=None, limit=50):
	filters = _tenant_filter(tenant=tenant)
	or_filters = None
	if search:
		or_filters = [
			["Transport Load", "name", "like", f"%{search}%"],
			["Transport Load", "origin_city", "like", f"%{search}%"],
			["Transport Load", "destination_city", "like", f"%{search}%"],
		]
	rows = frappe.get_all(
		"Transport Load",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"posting_date",
			"load_type",
			"origin_city",
			"destination_city",
			"vehicle",
			"driver",
			"status",
			"total_bilties",
			"total_freight",
			"receiver_pay_amount",
			"paid_amount",
		],
		limit_page_length=cint(limit) or 50,
		order_by="modified desc",
	)
	return {
		"rows": [
			{
				"id": row.name,
				"label": row.name,
				"posting_date": row.posting_date,
				"load_type": row.load_type,
				"origin_city": row.origin_city,
				"destination_city": row.destination_city,
				"vehicle": row.vehicle,
				"driver": row.driver,
				"status": row.status,
				"total_bilties": row.total_bilties,
				"total_freight": row.total_freight,
				"receiver_pay_amount": row.receiver_pay_amount,
				"paid_amount": row.paid_amount,
			}
			for row in rows
		]
	}


@frappe.whitelist()
def get_fleet_map(tenant=None):
	rows = list_vehicles(tenant=tenant, limit=200)["rows"]
	return {
		"center": {"lat": 31.5204, "lng": 74.3587, "label": "Lahore"},
		"vehicles": [
			{
				"id": row["id"],
				"label": row["label"],
				"status": row["status"],
				"lat": row["lat"] or 31.5204,
				"lng": row["lng"] or 74.3587,
				"driver": row["driver"],
				"owner": row["owner"],
			}
			for row in rows
		],
	}


@frappe.whitelist()
def get_record(kind, name, tenant=None):
	config = _record_config(kind)
	_assert_record_tenant(config["doctype"], name, tenant=tenant)
	doc = frappe.get_doc(config["doctype"], name)
	return _record_payload(kind, doc)


@frappe.whitelist()
def update_record(kind, name, data=None, tenant=None, **kwargs):
	config = _record_config(kind)
	_assert_record_tenant(config["doctype"], name, tenant=tenant)
	doc = frappe.get_doc(config["doctype"], name)
	payload = _payload(data, **kwargs)
	updates = _normalize_update_data(kind, payload)
	if not updates:
		frappe.throw(_("No editable fields were provided."))

	for fieldname, value in updates.items():
		doc.set(fieldname, value)
	doc.save(ignore_permissions=True)
	return _record_payload(kind, doc)
