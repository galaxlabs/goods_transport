# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from goods_transport.services.tenant import validate_same_tenant, validate_tenant_reference


class TransportLoad(Document):
	def validate(self):
		validate_tenant_reference(self)
		validate_same_tenant("Transport Vehicle", self.vehicle, self.tenant, "Vehicle")
		validate_same_tenant("Transport Driver", self.driver, self.tenant, "Driver")
		validate_same_tenant("Vehicle Owner", self.vehicle_owner, self.tenant, "Vehicle Owner")
		self._validate_bilties()
		self._set_totals()

	def _validate_bilties(self):
		seen_bilties = set()
		for row in self.bilties:
			if not row.bilty_no:
				frappe.throw(_("Bilty No is required for every load row."))
			if row.bilty_no in seen_bilties:
				frappe.throw(_("Bilty No {0} is duplicated in this load.").format(row.bilty_no))
			seen_bilties.add(row.bilty_no)

			validate_same_tenant("Commodity Customer", row.sender_customer, self.tenant, "Sender")
			validate_same_tenant("Commodity Customer", row.receiver_customer, self.tenant, "Receiver")
			validate_same_tenant("Commodity Customer", row.invoice_customer, self.tenant, "Invoice Customer")

	def _set_totals(self):
		self.total_bilties = len(self.bilties)
		self.total_freight = sum(flt(row.freight_amount) for row in self.bilties)
		self.paid_amount = sum(flt(row.freight_amount) for row in self.bilties if row.payment_type == "Paid")
		self.receiver_pay_amount = sum(
			flt(row.freight_amount) for row in self.bilties if row.payment_type == "Receiver Pay"
		)

