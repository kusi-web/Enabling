# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_checkers_requires = fields.Boolean(string='Checkers Required', default=False)
    is_second_validation = fields.Boolean(string='Second Validation', default=False)
    tolerance_percentage = fields.Char(string='Tolerance Percentage', default='10')
    tolerance_price = fields.Monetary(string='Tolerance Price', default=0.0)
    first_approver_ids = fields.Many2many('res.users', 'company_first_approver_rel', 'company_id', 'user_id', 
                                          string='First Approvers')
    second_approver_ids = fields.Many2many('res.users', 'company_second_approver_rel', 'company_id', 'user_id', 
                                           string='Second Approvers')
    group_by_company = fields.Selection([
        ('wm', 'WM'),
        ('wr', 'WR')
    ], string='Group By Company')
    bool_toi_pakihi_rules = fields.Boolean(string='Toi Pakihi Rules', default=False)
