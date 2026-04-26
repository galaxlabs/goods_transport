# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from goods_transport.api.settings import (
	get_map_settings,
	get_tenant_print_settings,
	get_whatsapp_settings,
	update_map_settings,
	update_tenant_print_settings,
	update_whatsapp_settings,
)
from goods_transport.tests.test_tenant_foundation import add_role, make_tenant, make_tenant_profile, make_user


class TestTenantSettings(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_whatsapp_settings_resolve_tenant_from_current_user(self):
		user = make_user("settings.admin@example.com", "Settings Admin")
		add_role(user.name, "Tenant Admin")
		own_tenant = make_tenant("Settings Tenant")
		other_tenant = make_tenant("Other Settings Tenant")
		make_tenant_profile(user.name, own_tenant.name)

		frappe.set_user(user.name)
		result = update_whatsapp_settings(
			tenant=other_tenant.name,
			enabled=1,
			sandbox_mode=1,
			account_sid="AC123",
			auth_token_password="secret-token",
			from_whatsapp_number="+14155238886",
		)

		self.assertEqual(result["tenant"], own_tenant.name)
		self.assertEqual(result["enabled"], 1)
		self.assertNotIn("auth_token_password", result)
		self.assertTrue(frappe.db.exists("Tenant WhatsApp Setting", {"tenant": own_tenant.name}))
		self.assertFalse(frappe.db.exists("Tenant WhatsApp Setting", {"tenant": other_tenant.name}))

	def test_map_settings_do_not_expose_password_field(self):
		user = make_user("maps.admin@example.com", "Maps Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Maps Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		updated = update_map_settings(
			enabled=1,
			distance_calculation_enabled=1,
			route_preview_enabled=1,
			live_tracking_enabled=0,
			google_api_key_password="maps-secret",
		)
		fetched = get_map_settings()

		self.assertEqual(updated["tenant"], tenant.name)
		self.assertEqual(fetched["enabled"], 1)
		self.assertEqual(fetched["distance_calculation_enabled"], 1)
		self.assertNotIn("google_api_key_password", fetched)

	def test_print_settings_can_create_default_per_print_type(self):
		user = make_user("print.admin@example.com", "Print Admin")
		add_role(user.name, "Tenant Admin")
		tenant = make_tenant("Print Tenant")
		make_tenant_profile(user.name, tenant.name)

		frappe.set_user(user.name)
		result = update_tenant_print_settings(
			print_type="Bilty",
			title="Standard Bilty",
			terms_and_conditions="Goods accepted subject to company policy.",
			language="English",
			is_default=1,
		)
		settings = get_tenant_print_settings(print_type="Bilty")

		self.assertEqual(result["tenant"], tenant.name)
		self.assertEqual(result["print_type"], "Bilty")
		self.assertEqual(len(settings), 1)
		self.assertEqual(settings[0]["is_default"], 1)
