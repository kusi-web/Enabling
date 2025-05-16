# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools


class AccountAccount(models.Model):
    _inherit = "account.account"

    def update_companies(self):
        if not self.code or not self.company_id:
            return

        other_companies = self.env["res.company"].search([
            ('id', '!=', self.company_id.id)
        ])
        
        for company in other_companies:
            coa = self.env["account.account"].with_company(company).search([
                ('code', '=', self.code),
                ('company_id', '=', company.id)
            ], limit=1)
            
            if coa:
                vals = {
                    'name': self.name,
                    'x_mgmt_level1': self.x_mgmt_level1,
                    'x_mgmt_level2': self.x_mgmt_level2,
                    'x_stat_level1': self.x_stat_level1,
                    'x_stat_level2': self.x_stat_level2,
                    'x_cashflow': self.x_cashflow,
                    'account_type': self.account_type,
                    'reconcile': self.reconcile,
                    'deprecated': self.deprecated,
                    'group_id': self.group_id.id,
                }
                coa.write(vals)
            else:
                self.with_company(company).copy(default={
                    'company_id': company.id,
                    'code': self.code,
                    'name': self.name
                })

    def update_wm_companies(self):
        if not self.code or not self.company_id:
            return

        wm_companies = self.env["res.company"].search([
            ('id', '!=', self.company_id.id),
            ('group_by_company', '=', 'wm')
        ])
        
        for company in wm_companies:
            coa = self.env["account.account"].with_company(company).search([
                ('code', '=', self.code),
                ('company_id', '=', company.id)
            ], limit=1)
            
            if coa:
                vals = {
                    'name': self.name,
                    'x_mgmt_level1': self.x_mgmt_level1,
                    'x_mgmt_level2': self.x_mgmt_level2,
                    'x_stat_level1': self.x_stat_level1,
                    'x_stat_level2': self.x_stat_level2,
                    'x_cashflow': self.x_cashflow,
                    'account_type': self.account_type,
                    'reconcile': self.reconcile,
                    'deprecated': self.deprecated,
                    'group_id': self.group_id.id,
                }
                coa.write(vals)
            else:
                self.with_company(company).copy(default={
                    'company_id': company.id,
                    'code': self.code,
                    'name': self.name
                })

    def update_wr_companies(self):
        if not self.code or not self.company_id:
            return

        wr_companies = self.env["res.company"].search([
            ('id', '!=', self.company_id.id),
            ('group_by_company', '=', 'wr')
        ])
        
        for company in wr_companies:
            coa = self.env["account.account"].with_company(company).search([
                ('code', '=', self.code),
                ('company_id', '=', company.id)
            ], limit=1)
            
            if coa:
                vals = {
                    'name': self.name,
                    'x_mgmt_level1': self.x_mgmt_level1,
                    'x_mgmt_level2': self.x_mgmt_level2,
                    'x_stat_level1': self.x_stat_level1,
                    'x_stat_level2': self.x_stat_level2,
                    'x_cashflow': self.x_cashflow,
                    'account_type': self.account_type,
                    'reconcile': self.reconcile,
                    'deprecated': self.deprecated,
                    'group_id': self.group_id.id,
                }
                coa.write(vals)
            else:
                self.with_company(company).copy(default={
                    'company_id': company.id,
                    'code': self.code,
                    'name': self.name
                })
