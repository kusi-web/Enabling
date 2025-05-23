# -*- coding: utf-8 -*-

import re
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger(__name__)


class AccountAssetBatch(models.TransientModel):
	_name="account.asset.batch"
	
	asset_ids = fields.Many2many('account.asset',string="Asset Selected",required=True,domain="[('state','=','draft')]")
     
	def batch_confirm(self):
		for line in self.asset_ids:
			line.validate()
		return True
