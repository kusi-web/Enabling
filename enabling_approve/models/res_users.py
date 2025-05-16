# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _


class ResUsers(models.Model):
    _inherit = "res.users"

    first_approver = fields.Boolean(string="First Approver for Vendor Bills")
    second_approver = fields.Boolean(string="Second Approver for Vendor Bills")
