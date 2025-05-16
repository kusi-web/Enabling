# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    hide = fields.Boolean("Hide")
