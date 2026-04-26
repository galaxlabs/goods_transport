# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

from frappe.model.document import Document

from goods_transport.services.tenant import validate_tenant_reference


class TenantBranch(Document):
	def validate(self):
		validate_tenant_reference(self)
