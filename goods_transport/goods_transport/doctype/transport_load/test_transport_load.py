# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from goods_transport.api.onboarding import register_local_load
from goods_transport.tests.test_tenant_foundation import add_role, make_tenant, make_tenant_profile, make_user


class TestTransportLoad(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_register_local_load_creates_customers_and_totals(self):
		user = make_user("tenant.load.admin@example.com", "Load Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Local Load Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		result = register_local_load(
			origin_city="Lahore",
			destination_city="Karachi",
			bilties=[
				{
					"bilty_no": "LHR-001",
					"sender_name": "Sender One",
					"sender_mobile": "03001110001",
					"receiver_name": "Receiver One",
					"receiver_address": "Receiver Market",
					"goods_description": "Cotton",
					"freight_amount": 1000,
					"payment_type": "Paid",
				},
				{
					"bilty_no": "LHR-002",
					"sender_name": "Sender Two",
					"receiver_name": "Receiver Two",
					"freight_amount": 1500,
					"payment_type": "Receiver Pay",
				},
			],
		)

		self.assertEqual(result["tenant"], tenant.name)
		self.assertEqual(result["total_bilties"], 2)
		self.assertEqual(result["total_freight"], 2500)
		self.assertEqual(result["paid_amount"], 1000)
		self.assertEqual(result["receiver_pay_amount"], 1500)
		self.assertTrue(frappe.db.exists("Commodity Customer", {"tenant": tenant.name, "customer_name": "Sender One"}))

