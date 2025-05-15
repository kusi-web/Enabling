# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountReconcileModelLine(models.Model):
    _inherit = 'account.reconcile.model.line'

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account_id(self):
        if self.analytic_account_id and self.analytic_account_id.sale_tax_id.id is not False:
            self.tax_ids = [(6, 0, [self.analytic_account_id.sale_tax_id.id])]
        else:
            self.tax_ids = False
