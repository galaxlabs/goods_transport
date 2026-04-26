# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

from frappe.model.document import Document

from goods_transport.services.tenant import validate_same_tenant, validate_tenant_reference


class TransportDriver(Document):
	def validate(self):
		validate_tenant_reference(self)
		validate_same_tenant("Vehicle Owner", self.linked_vehicle_owner, self.tenant, "Linked Vehicle Owner")
