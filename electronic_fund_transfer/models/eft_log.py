# -*- coding: utf-8 -*-


from odoo import models, fields, api


class EFTLogEntry(models.Model):
    _name = 'eft.log.entry'
    _description = "This Table Contains Record Of User Who Print EFT Report"

    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    created_date = fields.Datetime(string="Created Date", default=fields.Datetime.now())
    payment_id = fields.Many2one("account.payment", string="Payment")
