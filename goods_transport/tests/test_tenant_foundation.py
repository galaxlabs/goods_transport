# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from goods_transport.api.tenant import get_current_user_profile, get_user_tenant
from goods_transport.services import permissions
from goods_transport.setup.install import ensure_roles


def make_user(email: str, first_name: str):
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)

	return frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"enabled": 1,
			"user_type": "System User",
			"new_password": "Test@12345",
		}
	).insert(ignore_permissions=True)


def add_role(user: str, role: str):
	user_doc = frappe.get_doc("User", user)
	if any(row.role == role for row in user_doc.roles):
		return
	user_doc.append("roles", {"role": role})
	user_doc.save(ignore_permissions=True)


def make_tenant(tenant_name: str):
	existing = frappe.db.get_value("Transport Tenant", {"tenant_name": tenant_name})
	if existing:
		return frappe.get_doc("Transport Tenant", existing)

	return frappe.get_doc(
		{
			"doctype": "Transport Tenant",
			"tenant_name": tenant_name,
			"company_type": "Transport",
			"registration_type": "Company",
			"phone": "03001234567",
			"email": f"{tenant_name.lower().replace(' ', '.')}@example.com",
			"city": "Lahore",
			"province": "Punjab",
			"status": "Active",
			"default_currency": "PKR",
		}
	).insert(ignore_permissions=True)


def make_tenant_profile(user: str, tenant: str, role_type="Tenant Admin"):
	existing = frappe.db.get_value("Tenant User Profile", {"user": user})
	if existing:
		return frappe.get_doc("Tenant User Profile", existing)

	return frappe.get_doc(
		{
			"doctype": "Tenant User Profile",
			"tenant": tenant,
			"user": user,
			"role_type": role_type,
			"is_active": 1,
		}
	).insert(ignore_permissions=True)


def make_vehicle_owner(tenant: str, owner_name: str):
	return frappe.get_doc(
		{
			"doctype": "Vehicle Owner",
			"tenant": tenant,
			"owner_name": owner_name,
			"registration_type": "Individual",
			"mobile": "03001234567",
			"status": "Active",
		}
	).insert(ignore_permissions=True).name


def make_driver(tenant: str, driver_name: str):
	return frappe.get_doc(
		{
			"doctype": "Transport Driver",
			"tenant": tenant,
			"driver_name": driver_name,
			"mobile": "03007654321",
			"status": "Active",
		}
	).insert(ignore_permissions=True).name


class TestTenantFoundation(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		ensure_roles()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_get_user_tenant_returns_current_users_tenant(self):
		user = make_user("tenant.user@example.com", "Tenant")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Alpha Logistics")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		result = get_user_tenant()

		self.assertEqual(result["name"], tenant.name)
		self.assertEqual(result["tenant_name"], "Alpha Logistics")

	def test_get_current_user_profile_returns_active_profile(self):
		user = make_user("ops.user@example.com", "Ops")
		add_role(user.name, "Transport Manager")
		tenant = make_tenant("Beta Carriers")
		profile = make_tenant_profile(user.name, tenant.name, role_type="Transport Manager")

		frappe.set_user(user.name)
		result = get_current_user_profile()

		self.assertEqual(result["name"], profile.name)
		self.assertEqual(result["tenant"], tenant.name)
		self.assertEqual(result["role_type"], "Transport Manager")

	def test_tenant_permission_query_condition_restricts_records(self):
		user = make_user("account.user@example.com", "Account")
		add_role(user.name, "Accountant")
		tenant = make_tenant("Gamma Movers")
		make_tenant_profile(user.name, tenant.name, role_type="Accountant")

		condition = permissions.get_transport_vehicle_query(user.name)

		self.assertIn("`tabTransport Vehicle`.`tenant` =", condition)
		self.assertIn(tenant.name, condition)

	def test_vehicle_number_must_be_unique_within_same_tenant(self):
		tenant = make_tenant("Delta Transport")
		owner = make_vehicle_owner(tenant.name, "Owner One")
		driver = make_driver(tenant.name, "Driver One")

		frappe.get_doc(
			{
				"doctype": "Transport Vehicle",
				"tenant": tenant.name,
				"vehicle_number": "LES-1234",
				"vehicle_type": "Truck",
				"vehicle_owner": owner,
				"driver": driver,
				"status": "Available",
			}
		).insert(ignore_permissions=True)

		with self.assertRaises(ValidationError):
			frappe.get_doc(
				{
					"doctype": "Transport Vehicle",
					"tenant": tenant.name,
					"vehicle_number": "LES-1234",
					"vehicle_type": "Truck",
					"vehicle_owner": owner,
					"driver": driver,
					"status": "Available",
				}
			).insert(ignore_permissions=True)

	def test_same_vehicle_number_is_allowed_across_tenants(self):
		tenant_one = make_tenant("Echo Transport")
		tenant_two = make_tenant("Foxtrot Transport")
		owner_one = make_vehicle_owner(tenant_one.name, "Owner Echo")
		owner_two = make_vehicle_owner(tenant_two.name, "Owner Foxtrot")
		driver_one = make_driver(tenant_one.name, "Driver Echo")
		driver_two = make_driver(tenant_two.name, "Driver Foxtrot")

		first = frappe.get_doc(
			{
				"doctype": "Transport Vehicle",
				"tenant": tenant_one.name,
				"vehicle_number": "ABC-999",
				"vehicle_type": "Truck",
				"vehicle_owner": owner_one,
				"driver": driver_one,
				"status": "Available",
			}
		).insert(ignore_permissions=True)

		second = frappe.get_doc(
			{
				"doctype": "Transport Vehicle",
				"tenant": tenant_two.name,
				"vehicle_number": "ABC-999",
				"vehicle_type": "Truck",
				"vehicle_owner": owner_two,
				"driver": driver_two,
				"status": "Available",
			}
		).insert(ignore_permissions=True)

		self.assertTrue(first.name)
		self.assertTrue(second.name)
