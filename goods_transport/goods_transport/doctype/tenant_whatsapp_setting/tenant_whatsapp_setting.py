# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from goods_transport.services.tenant import validate_tenant_reference


class TenantWhatsAppSetting(Document):
	def validate(self):
		validate_tenant_reference(self)
		existing = frappe.db.get_value(
			"Tenant WhatsApp Setting",
			{"tenant": self.tenant, "name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(_("Only one WhatsApp setting is allowed per tenant."))
