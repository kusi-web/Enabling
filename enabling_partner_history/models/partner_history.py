
from odoo import api, models, fields, _
from xlrd import open_workbook 
import base64
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class PartnerHistory(models.Model):    
    _name = 'partner.history'
    partner_id = fields.Many2one('res.partner',string ='Customer ID')
    sage_document = fields.Char(string ='Sage Document ID')
    transaction_type = fields.Char(string ='Transaction Type')
    document_type = fields.Char(string = 'Document Type')
    fiscyr = fields.Char(string ='Fiscal Year')
    fiscper = fields.Char(string ='Fiscal Period')
    inv_amount = fields.Char(string ='Invoice Amount')
    inv_tax = fields.Char(string ='Invoice Tax')
    inv_disc = fields.Char(string ='Invoice Discount')
    date_post = fields.Char(string ='Date Posted')
    date_paid = fields.Char(string='Date Paid')

class ResPartner(models.Model):
    _inherit = 'res.partner'
    history_ids = fields.One2many('partner.history','partner_id',string='Partner History')
    history_count = fields.Integer(string='Historical Count', compute='_compute_hist_count')
    toi_pakihi=fields.Boolean(string="Toi Pakihi",default=False)
    @api.depends('history_ids')
    def _compute_hist_count(self):
        for record in self:
            record.history_count = len(record.history_ids)

    def action_view_history(self):
        self.ensure_one()
        action = {
            'res_model': 'partner.history',
            'type': 'ir.actions.act_window',
        }
        action.update({
            'name': _("History generated"),
            'domain': [('id', 'in', self.history_ids.ids)],
            'view_mode': 'tree,form',
            })
        return action
