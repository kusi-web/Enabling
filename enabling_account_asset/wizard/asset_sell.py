# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetSell(models.TransientModel):
	_inherit = 'account.asset.sell'

	analytic_account_id = fields.Many2one('account.analytic.account',string="Analytic Account")
	disposal_sell_reason = fields.Text("Disposal/Sell Reason")
	company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
	gain_account_id = fields.Many2one('account.account',string="Gain/Loss Account", domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", related='company_id.gain_account_id', help="Account used to write the journal item in case of gain", readonly=False)
	loss_account_id = fields.Many2one('account.account',string="Gain/Loss Account", domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", related='company_id.loss_account_id', help="Account used to write the journal item in case of loss", readonly=False)


	def do_action(self):
		self.ensure_one()
		gain_account_id = self.gain_account_id
		loss_account_id = self.loss_account_id
		invoice_line = self.env['account.move.line'] if self.action == 'dispose' else self.invoice_line_id or self.invoice_id.invoice_line_ids
		return self.asset_id.set_to_close(invoice_line_id=invoice_line, date=invoice_line.move_id.invoice_date, gain_account_id=self.gain_account_id, loss_account_id=self.loss_account_id, analytic_account_id=self.analytic_account_id)

