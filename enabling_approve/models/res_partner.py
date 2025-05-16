# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # first_part_approver_ids = fields.Many2many('res.users', 'first_approver_part_rel', 'user_id', 'company_id',
    #                                        string='First Approvers')
    # second_part_approver_ids = fields.Many2many('res.users', 'second_approver_part_rel', 'user_id', 'company_id',
    #                                        string='Second Approvers')

    """ adds tracking """
    name = fields.Char(index=True, tracking=True)
    vat = fields.Char(string='Tax ID', index=True, help="The Tax Identification Number. Complete it if the contact is subjected to government taxes. Used in some legal statements.", tracking=True)
    street = fields.Char(tracking=True)
    street2 = fields.Char(tracking=True)
    #suburb = fields.Char(string="Suburb", tracking=True)
    zip = fields.Char(change_default=True, tracking=True)
    city = fields.Char(tracking=True)
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]", tracking=True)
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', tracking=True)
    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5), tracking=True)
    email = fields.Char(tracking=True)
    mobile = fields.Char(tracking=True)
    
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        tracking=True)
        
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        tracking=True)
