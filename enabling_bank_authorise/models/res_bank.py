# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    show_authorise = fields.Boolean(compute='_compute_show_authorise')

    @api.depends('company_id.approver_ids')
    def _compute_show_authorise(self):
        for record in self:
            if self.env.uid in record.company_id.approver_ids.ids:
                record.show_authorise = True
            else:
                record.show_authorise = False
