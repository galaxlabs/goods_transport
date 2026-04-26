# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from goods_transport.services.tenant import validate_same_tenant, validate_tenant_reference


class TenantUserProfile(Document):
	def validate(self):
		validate_tenant_reference(self)
		self._validate_unique_user()
		self._validate_branch_tenant()
		self._validate_linked_records()

	def _validate_unique_user(self):
		existing = frappe.db.get_value(
			"Tenant User Profile",
			{"user": self.user, "name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(_("User {0} already has a tenant profile.").format(self.user))

	def _validate_branch_tenant(self):
		if not self.branch:
			return

		branch_tenant = frappe.db.get_value("Tenant Branch", self.branch, "tenant")
		if branch_tenant != self.tenant:
			frappe.throw(_("Branch must belong to the same tenant as the profile."))

	def _validate_linked_records(self):
		validate_same_tenant("Commodity Customer", self.linked_customer, self.tenant, "Linked Customer")
		validate_same_tenant("Transport Driver", self.linked_driver, self.tenant, "Linked Driver")
		validate_same_tenant("Vehicle Owner", self.linked_vehicle_owner, self.tenant, "Linked Vehicle Owner")
