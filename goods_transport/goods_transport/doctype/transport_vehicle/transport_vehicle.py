# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from goods_transport.services.tenant import validate_same_tenant, validate_tenant_reference


class TransportVehicle(Document):
	def validate(self):
		validate_tenant_reference(self)
		validate_same_tenant("Vehicle Owner", self.vehicle_owner, self.tenant, "Owner")
		validate_same_tenant("Transport Driver", self.driver, self.tenant, "Driver")
		self._validate_unique_vehicle_number()

	def _validate_unique_vehicle_number(self):
		existing = frappe.db.get_value(
			"Transport Vehicle",
			{
				"tenant": self.tenant,
				"vehicle_number": self.vehicle_number,
				"name": ["!=", self.name],
			},
			"name",
		)
		if existing:
			frappe.throw(_("Vehicle number must be unique within the same tenant."))
