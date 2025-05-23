# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _

class ResCompany(models.Model):
	_inherit = "res.company"

	value_clearing_account = fields.Many2one('account.account',string="Clearing Account", domain="[('deprecated', '=', False), ('company_id', '=', id)]")
	revalue_clearing_account = fields.Many2one('account.account',string="Clearing Account", domain="[('deprecated', '=', False), ('company_id', '=', id)]")
