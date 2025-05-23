# -*- coding: utf-8 -*-
from odoo import exceptions, fields, models ,api, _
from odoo.exceptions import ValidationError
import io
from datetime import datetime, timedelta, date
import xlrd
from xlrd import open_workbook
import csv
import base64
import sys
from odoo.tools import pycompat
import logging
_logger = logging.getLogger(__name__)

class ImportAssetRevaluation(models.TransientModel):
    _name = 'import.asset.revaluation'
    _description = 'Import Asset Revaluations'

    select_file = fields.Selection([('csv', 'CSV File'),('xls', 'XLS File')], string='Select', required=True)
    data_file = fields.Binary(string="File", required=True)

    def import_asset_revaluation(self):
        file_data = False
        if self.select_file and self.data_file:
            if self.select_file == 'csv' :
                csv_reader_data = pycompat.csv_reader(io.BytesIO(base64.decodestring(self.data_file)),delimiter=",")
                csv_reader_data = iter(csv_reader_data)
                next(csv_reader_data)
                file_data = csv_reader_data
            elif self.select_file == 'xls':
                file_datas = base64.decodestring(self.data_file)
                workbook = xlrd.open_workbook(file_contents=file_datas)
                sheet = workbook.sheet_by_index(0)
                result = []
                data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
                data.pop(0)
                file_data = data
        else:
            raise ValidationError(_('Please select file and type of file properly'))
        
        account_asset_obj = self.env['account.asset']
        account_account_obj = self.env['account.account']
        account_analytic_account_obj = self.env['account.analytic.account']

        for row in file_data:
            ids=[]
            asset_rec = account_asset_obj.search([('name', '=', row[0])])
            if not asset_rec:
                raise ValidationError("Asset with name '%s' could not be located ! " % (row[0]))
            if row[2]:
                date = datetime.strptime(str(row[2]), "%d-%m-%Y").date()
            else:
                date = fields.Date.today()
            row_len = len(row)
            account_asset_rec = row_len > 5 and row[5] and account_account_obj.search([('code', '=', row[5])], limit=1) or False
            account_asset_counterpart_rec = row_len > 6 and row[6] and account_account_obj.search([('code', '=', row[6])], limit=1) or False
            analytic_account_rec = row_len > 7 and row[7] and account_analytic_account_obj.search([('name', '=', row[7])], limit=1) or False

            if not account_asset_rec:
                account_asset_rec = asset_rec.account_asset_id
            if not account_asset_counterpart_rec:
                account_asset_counterpart_rec = asset_rec.company_id.revalue_clearing_account
            if not analytic_account_rec:
                analytic_account_rec = asset_rec.account_analytic_id
            
            vals={
                'asset_id': asset_rec.id,
                'name': row[1] or '',
                'date': date,
                'value_amount': row[3] or 0.0,
                'tax_value_amount': row[4] or 0.0,
                'book_reval':asset_rec.x_book_reval,
                'state': 'draft',
                'currency_id': asset_rec.currency_id and asset_rec.currency_id.id or False,
                'account_asset_id': account_asset_rec and account_asset_rec.id or False,
                'account_asset_counterpart_id': account_asset_counterpart_rec and account_asset_counterpart_rec.id or False,
                'analytic_account_id': analytic_account_rec and analytic_account_rec.id or False,
            }

            asset_revalue_obj = self.env['asset.revalue']
            asset_revalue_rec = asset_revalue_obj.create(vals)
            if asset_revalue_rec:
                asset_revalue_rec.modify()
        return True