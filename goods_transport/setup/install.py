# Copyright (c) 2026, Galaxy Labs and Contributors
# See license.txt

import frappe


APP_ROLES = [
	"SaaS Owner",
	"Tenant Admin",
	"Transport Manager",
	"Warehouse Manager",
	"Accountant",
	"Driver",
	"Vehicle Owner",
	"Customer",
]


def ensure_roles():
	for role_name in APP_ROLES:
		if frappe.db.exists("Role", role_name):
			continue
		frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)


def after_install():
	ensure_roles()


def after_migrate():
	ensure_roles()


def before_tests():
	ensure_roles()
