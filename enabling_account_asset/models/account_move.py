from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = "account.move.line" 

    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
        domain=[('deprecated', '=', False)],
        tracking=True)

    is_optional = fields.Boolean(string='Optional', default=False)