# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

from frappe.model.document import Document

from goods_transport.services.settings import update_default_print_setting
from goods_transport.services.tenant import validate_tenant_reference


class TenantPrintSetting(Document):
	def validate(self):
		validate_tenant_reference(self)

	def on_update(self):
		update_default_print_setting(self)
