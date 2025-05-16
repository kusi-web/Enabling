# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_distribute_expense(self):
        ''' Open the distribute.expense wizard to distribute expenses for the selected reconciliation model.
        :return: An action opening the distribute.expense wizard.
        '''
        return {
            'name': _('Distribute Expenses'),
            'res_model': 'distribute.expense',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    rec_model_id = fields.Many2one('account.reconcile.model',string="Rec Model")