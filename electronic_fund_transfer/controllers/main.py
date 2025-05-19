# -*- coding: utf-8 -*-


import json
from io import BytesIO, StringIO
from odoo.tools import html_escape
from odoo import http, tools, fields
from odoo.http import content_disposition, dispatch_rpc, request, Response
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
from pytz import timezone

import logging
_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Can not import xlsxwriter`.')


class ReportController(http.Controller):
    
    @http.route('/report/download/xlsx/<string:docids>/<eft_format>/<report_format>', type='http', auth='user', website=True)
    def report_download_xlsx(self, docids, eft_format, report_format):
        payments = request.env['account.payment'].sudo().browse([int(i) for i in docids.split(',') if i])
        _logger.info("\n\n\t\t payments ========== %s",payments)
        vendor_ids = []
        for payment in payments:
            parent_partners = request.env['res.partner'].search([('id', 'parent_of', [payment.partner_id.id])])
            _logger.info("\n\n\t\t parent_partners ========== %s",parent_partners)
            flag_list = []
            for part in parent_partners:
                if part.bank_account_count == 0:
                    flag_list.append(0)
                else:
                    flag_list.append(1)
            flag = 0 if flag_list.count(0) == len(flag_list) else 1
            if flag == 0:
                vendor_ids.append(payment.partner_id.name)
        # if vendor_ids:
        #     vendor_names = ""
        #     for vendor_id in vendor_ids:
        #         if vendor_names:
        #             vendor_names += ", " + vendor_id or ''
        #         else:
        #             vendor_names = vendor_id
        #     if vendor_names:
        #         error = {
        #             'code': 200,
        #             'message': "Please insert Bank account details for Vendors : " + vendor_names,
        #             'data': "Please insert Bank account details for Vendors : " + vendor_names
        #         }
        #         return request.make_response(html_escape(json.dumps(error)))
        #     else:
        #         error = {
        #             'code': 200,
        #             'message': "Please insert Bank account details for Vendors : ",
        #             'data': "Please insert Bank account details for Vendors : "
        #         }
        #         return request.make_response(html_escape(json.dumps(error)))

        if report_format == 'text':
            nz=timezone("NZ")
            file_data = StringIO()
            payments.write_text_file(file_data, eft_format)
            file_data.seek(0)
            data = file_data.getvalue()
            texthttpheaders = [
                ('Content-Type', 'text/*'
                                 'text/plain'),
                ('Content-Length', len(data)),
                (
                    'Content-Disposition',
                    content_disposition(eft_format.capitalize() + '_' + datetime.now().astimezone(nz).strftime('%Y-%m-%d') + '.txt')
                )
            ]
            return request.make_response(data, headers=texthttpheaders)

        if report_format == 'xlsx':
            nz=timezone("NZ")
            file_data = BytesIO()
            workbook = xlsxwriter.Workbook(file_data)
            payments.write_excel_workbook(workbook, eft_format)
            workbook.close()
            file_data.seek(0)
            xlsx = file_data.read(), 'xlsx'
            xlsx = xlsx[0]
            xlsxhttpheaders = [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Length', len(xlsx)),
                (
                    'Content-Disposition',
                    content_disposition(eft_format.capitalize() + '_' + datetime.now().astimezone(nz).strftime('%Y-%m-%d') + '.xlsx')
                )
            ]
            return request.make_response(xlsx, headers=xlsxhttpheaders)

    @http.route('/report/download/directdebit-eft/<string:report_format>/<string:eft_format>/<string:docids>', type='http', auth='user')
    def download_directdebit(self, report_format, eft_format, docids, duedate):
        # parse docids
        try:
            docids = [int(id) for id in docids.split(',') if id]
            payment_ids = request.env['account.payment'].sudo().browse(docids)
        except ValueError as e:
            raise UserError("Malformed request.")

        # check that a suitable bank account exists somewhere in the partner -> parent chain
        res_partner = request.env['res.partner']
        failed_partner_ids = []
        for payment in payment_ids:
            parent_partner_ids = res_partner.search([('id', 'parent_of', [payment.partner_id.id])])
            has_account = False

            for partner in parent_partner_ids:
                if partner.bank_account_count >= 0:
                    has_account = True
                    break
            
            if not has_account:
                failed_partner_ids.append(payment.partner_id.name)

        if len(failed_partner_ids) > 0:
            names = ', '.join(failed_partner_ids)
            raise ValidationError("Please ensure bank account details are available for these partners: %s" % names)

        if report_format == 'text' or report_format == 'xlsx':
            (headers, data) = payment_ids.eft_directdebit_export(report_format, eft_format, duedate)
            return request.make_response(data, headers=headers)
        else:
            raise UserError("Malformed request.")
