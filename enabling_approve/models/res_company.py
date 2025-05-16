# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    first_approver_ids = fields.Many2many('res.users', 'first_approver_company_rel', 'user_id', 'company_id',
                                           string='First Approvers')
    second_approver_ids = fields.Many2many('res.users', 'second_approver_company_rel', 'user_id', 'company_id',
                                           string='Second Approvers')
    bool_toi_pakihi_rules=fields.Boolean(string='Toi Pakihi Rules')
