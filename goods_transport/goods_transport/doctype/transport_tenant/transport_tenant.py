# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe.model.document import Document


class TransportTenant(Document):
	def validate(self):
		if not self.created_by_user:
			self.created_by_user = frappe.session.user
