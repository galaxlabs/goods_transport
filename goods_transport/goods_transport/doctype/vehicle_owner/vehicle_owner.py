# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

from frappe.model.document import Document

from goods_transport.services.tenant import validate_tenant_reference


class VehicleOwner(Document):
	def validate(self):
		validate_tenant_reference(self)
