# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['account.tax', 'mail.thread']
