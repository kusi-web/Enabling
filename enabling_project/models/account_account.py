# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools


class AccountAccount(models.Model):
    _inherit = "account.account"

    requires_project_code = fields.Boolean(string="Requires Project Code")
    requires_analytic_account = fields.Boolean(string="Requires Analytic Account")
    requires_analytic_tags = fields.Boolean(string="Requires Analytic Tags")
