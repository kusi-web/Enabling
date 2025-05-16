# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools


class AccountAccount(models.Model):
	_inherit = "account.account"


	def update_companies(self):
		if self.code and self.company_id.id:
			for company in self.env["res.company"].search([('id', '!=', self.company_id.id)]):
				coa = self.env["account.account"].sudo().search([('code', '=', self.code), ('company_id', '=', company.id)], limit=1)
				if coa:
					coa.name = self.name
					# Below 5 fields are declared in the UI. In case of any error comment below
					coa.x_mgmt_level1 = self.x_mgmt_level1
					coa.x_mgmt_level2 = self.x_mgmt_level2
					coa.x_stat_level1 = self.x_stat_level1
					coa.x_stat_level2 = self.x_stat_level2
					coa.x_cashflow = self.x_cashflow
					coa.user_type_id = self.user_type_id
					coa.reconcile = self.reconcile
					coa.deprecated = self.deprecated
					coa.group_id = self.group_id
				else:
					self.copy().write({'company_id': company.id, 'code': self.code, 'name': self.name})

	def update_wm_companies(self):
		if self.code and self.company_id.id:
			for company in self.env["res.company"].search([('id', '!=', self.company_id.id), ('group_by_company', '=', 'wm')]):
				coa = self.env["account.account"].sudo().search([('code', '=', self.code), ('company_id', '=', company.id)], limit=1)
				if coa:
					coa.name = self.name
					# Below 5 fields are declared in the UI. In case of any error comment below
					coa.x_mgmt_level1 = self.x_mgmt_level1
					coa.x_mgmt_level2 = self.x_mgmt_level2
					coa.x_stat_level1 = self.x_stat_level1
					coa.x_stat_level2 = self.x_stat_level2
					coa.x_cashflow = self.x_cashflow
					coa.user_type_id = self.user_type_id
					coa.reconcile = self.reconcile
					coa.deprecated = self.deprecated
					coa.group_id = self.group_id
				else:
					self.copy().write({'company_id': company.id, 'code': self.code, 'name': self.name})

	def update_wr_companies(self):
		if self.code and self.company_id.id:
			for company in self.env["res.company"].search([('id', '!=', self.company_id.id), ('group_by_company', '=', 'wr')]):
				coa = self.env["account.account"].sudo().search([('code', '=', self.code), ('company_id', '=', company.id)], limit=1)
				if coa:
					coa.name = self.name
					# Below 5 fields are declared in the UI. In case of any error comment below
					coa.x_mgmt_level1 = self.x_mgmt_level1
					coa.x_mgmt_level2 = self.x_mgmt_level2
					coa.x_stat_level1 = self.x_stat_level1
					coa.x_stat_level2 = self.x_stat_level2
					coa.x_cashflow = self.x_cashflow
					coa.user_type_id = self.user_type_id
					coa.reconcile = self.reconcile
					coa.deprecated = self.deprecated
					coa.group_id = self.group_id
				else:
					self.copy().write({'company_id': company.id, 'code': self.code, 'name': self.name})
