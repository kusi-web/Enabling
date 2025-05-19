# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    approver_ids = fields.Many2many('res.users', 'approver_company_rel', 'user_id', 'company_id', string='Approvers')
