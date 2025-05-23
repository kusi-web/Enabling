# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _

class ResCompany(models.Model):
	_inherit = "res.company"

	value_clearing_account = fields.Many2one('account.account', string="Value Addition Clearing Account", domain="[('deprecated', '=', False), ('company_id', '=', id)]")
	revalue_clearing_account = fields.Many2one('account.account', string="Revalue Clearing Account", domain="[('deprecated', '=', False), ('company_id', '=', id)]")
	gain_account_id = fields.Many2one('account.account', string="Gain Account", domain="[('deprecated', '=', False), ('company_id', '=', id)]")
	loss_account_id = fields.Many2one('account.account', string="Loss Account", domain="[('deprecated', '=', False), ('company_id', '=', id)]")
