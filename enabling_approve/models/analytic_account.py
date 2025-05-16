# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    approval_id = fields.Many2one('analytic.account.approval', string='Approval Configuration')
