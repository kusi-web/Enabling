from odoo import models, fields

class ReasonsToiPakihi(models.Model):
    _name = 'reasons.toi.pakihi'
    _description = 'Toi Pakihi Reasons'

    name = fields.Char(string='Name', required=True)