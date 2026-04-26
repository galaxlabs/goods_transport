# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from goods_transport.api.onboarding import (
	register_customer,
	register_driver,
	register_local_load,
	register_transport_company,
	register_vehicle,
	register_vehicle_owner,
)
from goods_transport.api.simple import (
	create_customer,
	create_vehicle,
	get_customers,
	get_dashboard,
	get_fleet_map,
	get_vehicles,
	list_customers,
	list_loads,
	list_vehicles,
)
from goods_transport.tests.test_tenant_foundation import add_role, make_tenant, make_tenant_profile, make_user


class TestOnboarding(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_register_transport_company_creates_tenant_admin_profile(self):
		result = register_transport_company(
			tenant_name="Onboard Transport",
			company_type="Transport",
			registration_type="Company",
			admin_email="onboard.admin@example.com",
			admin_first_name="Onboard",
			admin_password="Test@12345",
			phone="03001112222",
			city="Lahore",
			province="Punjab",
		)

		self.assertTrue(result["tenant"])
		self.assertEqual(result["tenant_name"], "Onboard Transport")
		self.assertEqual(result["admin_user"], "onboard.admin@example.com")
		self.assertEqual(result["profile"]["role_type"], "Tenant Admin")

		profile = frappe.get_doc("Tenant User Profile", result["profile"]["name"])
		self.assertEqual(profile.tenant, result["tenant"])
		self.assertEqual(profile.user, "onboard.admin@example.com")
		self.assertEqual(profile.is_active, 1)

	def test_customer_registration_uses_logged_in_users_tenant(self):
		user = make_user("tenant.customer.admin@example.com", "Customer Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Customer Registration Tenant")
		other_tenant = make_tenant("Customer Spoof Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		result = register_customer(
			tenant=other_tenant.name,
			customer_name="Acme Commodities",
			customer_type="Commodity Owner",
			mobile="03001230000",
			email="acme@example.com",
		)

		self.assertEqual(result["tenant"], tenant.name)
		self.assertEqual(result["customer_name"], "Acme Commodities")
		self.assertFalse(frappe.db.exists("Commodity Customer", {"tenant": other_tenant.name}))

	def test_driver_owner_and_vehicle_registration_use_transport_doctypes(self):
		user = make_user("tenant.vehicle.admin@example.com", "Vehicle Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Vehicle Registration Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		owner = register_vehicle_owner(owner_name="Self Owner", registration_type="Individual", can_drive_self=1)
		driver = register_driver(
			driver_name="Self Driver",
			mobile="03009998888",
			can_register_own_vehicle=1,
			linked_vehicle_owner=owner["name"],
		)
		vehicle = register_vehicle(
			vehicle_number="VR-100",
			vehicle_type="Truck",
			vehicle_owner=owner["name"],
			driver=driver["name"],
			capacity_weight=12,
			capacity_weight_unit="Ton",
		)

		self.assertEqual(owner["tenant"], tenant.name)
		self.assertEqual(driver["tenant"], tenant.name)
		self.assertEqual(vehicle["doctype"], "Transport Vehicle")
		self.assertEqual(vehicle["tenant"], tenant.name)
		self.assertEqual(vehicle["vehicle_owner"], owner["name"])
		self.assertEqual(vehicle["driver"], driver["name"])

	def test_simple_customer_api_returns_frontend_label_payload(self):
		user = make_user("tenant.simple.customer@example.com", "Simple Customer Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Simple Customer Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		result = create_customer(customer="Walk In Sender", mobile="03001234555", city="Lahore")

		self.assertEqual(result["doctype"], "Commodity Customer")
		self.assertEqual(result["label"], "Walk In Sender")
		self.assertEqual(result["customer"], result["id"])
		self.assertEqual(result["tenant"], tenant.name)

		options = get_customers(search="Walk In")
		self.assertIn({"id": result["id"], "label": "Walk In Sender"}, options)

	def test_simple_vehicle_api_auto_creates_owner_and_returns_label_payload(self):
		user = make_user("tenant.simple.vehicle@example.com", "Simple Vehicle Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Simple Vehicle Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		result = create_vehicle(vehicle="SIMPLE-100", owner="Simple Owner", driver="Simple Driver")

		self.assertEqual(result["doctype"], "Transport Vehicle")
		self.assertEqual(result["label"], "SIMPLE-100")
		self.assertEqual(result["vehicle"], result["id"])
		self.assertEqual(result["tenant"], tenant.name)
		self.assertTrue(result["vehicle_owner"])
		self.assertTrue(result["driver"])

		options = get_vehicles(search="SIMPLE")
		self.assertIn({"id": result["id"], "label": "SIMPLE-100"}, options)

	def test_dashboard_list_and_map_apis_return_tenant_records(self):
		user = make_user("tenant.dashboard@example.com", "Dashboard Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Dashboard Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		customer = create_customer(customer="Dashboard Sender", mobile="03001112223", city="Lahore", sync_to_erpnext=0)
		vehicle = create_vehicle(vehicle="DASH-100", owner="Dashboard Owner", driver="Dashboard Driver")
		frappe.db.set_value("Transport Vehicle", vehicle["id"], "current_lat", 31.5204)
		frappe.db.set_value("Transport Vehicle", vehicle["id"], "current_lng", 74.3587)
		register_local_load(
			origin_city="Lahore",
			destination_city="Multan",
			bilties=[
				{
					"bilty_no": "DASH-001",
					"sender_customer": customer["id"],
					"receiver_name": "Dashboard Receiver",
					"freight_amount": 1200,
					"payment_type": "Receiver Pay",
					"sync_parties_to_erpnext": 0,
				}
			],
		)

		dashboard = get_dashboard()
		self.assertGreaterEqual(dashboard["stats"]["customers"], 1)
		self.assertGreaterEqual(dashboard["stats"]["vehicles"], 1)
		self.assertGreaterEqual(dashboard["stats"]["loads"], 1)
		self.assertIn("vehicle_status", dashboard["charts"])

		self.assertTrue(any(row["label"] == "Dashboard Sender" for row in list_customers()["rows"]))
		self.assertTrue(any(row["label"] == "DASH-100" for row in list_vehicles()["rows"]))
		self.assertTrue(any(row["destination_city"] == "Multan" for row in list_loads()["rows"]))
		self.assertTrue(any(row["label"] == "DASH-100" for row in get_fleet_map()["vehicles"]))
