# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()

	if not filters.get("account"): return columns, []

	data = get_entries(filters)

	from erpnext.accounts.utils import get_balance_on
	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d[2])
		total_credit += flt(d[3])

	amounts_not_reflected_in_system = frappe.db.sql("""
		select sum(ifnull(jvd.debit_in_account_currency, 0) - ifnull(jvd.credit_in_account_currency, 0))
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 and jvd.account=%s
		and jv.posting_date > %s and jv.clearance_date <= %s and ifnull(jv.is_opening, 'No') = 'No'
		""", (filters["account"], filters["report_date"], filters["report_date"]))

	amounts_not_reflected_in_system = flt(amounts_not_reflected_in_system[0][0]) \
		if amounts_not_reflected_in_system else 0.0

	bank_bal = flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) \
		+ amounts_not_reflected_in_system

	data += [
		get_balance_row(_("Bank Statement balance as per General Ledger"), balance_as_per_system),
		[""]*len(columns),
		["",  _("Outstanding Cheques and Deposits to clear") , total_debit, total_credit, "", "", "", "", ""],
		get_balance_row(_("Cheques and Deposits incorrectly cleared"), amounts_not_reflected_in_system),
		[""]*len(columns),
		get_balance_row(_("Calculated Bank Statement balance"), bank_bal)
	]

	return columns, data

def get_columns():
	return [_("Posting Date") + ":Date:100", _("Journal Entry") + ":Link/Journal Entry:220",
		_("Debit") + ":Currency:120", _("Credit") + ":Currency:120",
		_("Against Account") + ":Link/Account:200", _("Reference") + "::100", 
		_("Ref Date") + ":Date:110", _("Clearance Date") + ":Date:110", _("Currency") + ":Link/Currency:70"
	]

def get_entries(filters):
	entries = frappe.db.sql("""select
			jv.posting_date, jv.name, jvd.debit_in_account_currency, jvd.credit_in_account_currency,
			jvd.against_account, jv.cheque_no, jv.cheque_date, jv.clearance_date, jvd.account_currency
		from
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1
			and jvd.account = %(account)s and jv.posting_date <= %(report_date)s
			and ifnull(jv.clearance_date, '4000-01-01') > %(report_date)s
			and ifnull(jv.is_opening, 'No') = 'No'
		order by jv.posting_date DESC,jv.name DESC""", filters, as_list=1)

	return entries

def get_balance_row(label, amount):
	if amount > 0:
		return ["", '"' + label + '"', amount, 0, "", "", "", "", ""]
	else:
		return ["", '"' + label + '"', 0, abs(amount), "", "", "", "", ""]