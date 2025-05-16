# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class DistributeExpense(models.TransientModel):
    _name = 'distribute.expense'
    _description = 'Distribute Expenses'

    vendor_bill_amount = fields.Float(string='Vendor Bill amount', required=True)
    label = fields.Char(string='Label', required=True)
    reconciliation_model = fields.Many2one('account.reconcile.model', string='Reconciliation model', required=True)

    def action_confirm(self):
        if self._context.get('active_model') == 'account.move':
            move = self.env['account.move'].browse(self._context.get('active_id'))
            lines = []
            for line in self.reconciliation_model.line_ids.filtered(lambda l: l.amount_type == 'percentage'):
                amount = float(line.amount_string) * self.vendor_bill_amount / 100
                lines.append(
                    (0, 0, {
                        'name': self.label,
                        'price_unit': amount,
                        'rec_model_id':self.reconciliation_model.id,
                        'account_id': line.account_id.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'journal_id': line.journal_id.id,
                        'tax_ids': [(6, 0, line.tax_ids.ids)]
                    }))
            move.write({'invoice_line_ids': lines})
