# -*- coding: utf-8 -*-

from odoo import fields, models


class AnalyticAccountApproval(models.Model):
    _name = 'analytic.account.approval'
    _description = 'Analytic Account Approval Configuration'

    name = fields.Char('Name', required=True)
    approval_user_ids = fields.One2many('analytic.approval.user', 'approval_id', string='Approval Users')


class AnalyticApprovalUser(models.Model):
    _name = 'analytic.approval.user'
    _description = 'Analytic Approval User Configuration'

    approval_id = fields.Many2one('analytic.account.approval', string='Approval Configuration', required=True)
    from_amount = fields.Float('From Amount', required=True)
    to_amount = fields.Float('To Amount', required=True)
    user_ids = fields.Many2many('res.users', string='Users')
    required_second_approval = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Required Second Approval', default='no')
    second_approver_user_ids = fields.Many2many('res.users', 'analytic_second_approver_rel', 
                                              'approval_user_id', 'user_id', string='Second Approvers')
