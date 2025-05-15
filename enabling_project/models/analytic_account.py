# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax")
    sale_tax_id = fields.Many2one('account.tax', string="Default Sales Tax")

