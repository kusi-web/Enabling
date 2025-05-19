# -*- coding: utf-8 -*-


from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError  #, Warning
from odoo.tools import float_round
from odoo.http import content_disposition

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone
from io import BytesIO, StringIO
import re

import logging
_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Can not import xlsxwriter`.')


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    eft_format_id = fields.Selection(related="journal_id.eft_format", string="EFT Format", store=True)
    status_eft = fields.Selection([('false', 'Pending EFT'), ('true', 'DONE EFT')], default='false',
                                  string="EFT Status")
    log_ids = fields.One2many("eft.log.entry", 'payment_id', string="Logs")
    partner_bank_acc_id = fields.Many2one('res.partner.bank', related='move_id.partner_bank_id', string='Recipient Bank', tracking=True,
                                      help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.',
                                      check_company=True)

    def write_text_file(self, file_data, eft_format):
        if eft_format == 'asb':
            dt_string = datetime.now().strftime("%d%m%Y%H%M%S")
            datas = self.export_asb_eft_report(dt_string)
            for each_account in datas["rows"].keys():
                for each_row_list in datas["rows"][each_account]:
                    for data_column_count in range(len(each_row_list)):
                        file_data.write(str(each_row_list[data_column_count]))
                        if data_column_count<len(each_row_list)-1:
                            file_data.write(',')
                    file_data.write("\r\n")

            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'asb' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

        if eft_format == 'anz':
            datas = self.export_anz_eft_report()
            total_amount = [each_payment.amount for each_payment in self.filtered(
                lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft")]
            # _logger.info('total_amount...',total_amount)
            # _logger.info('sum_amount....',sum(total_amount))
            amount = ('%.2f' % sum(total_amount)).replace(".", "")

            # account_numbers = [each_payment.partner_bank_id.acc_number for each_payment in self.filtered(
            #         lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft") if
            #                        each_payment.partner_id.bank_ids]
            account_numbers = []
            for each_payment in self.filtered(lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft"):
                partner_bank_id = self.env['res.partner.bank']
                if each_payment.reconciled_invoices_count > 0 and each_payment.reconciled_invoice_ids:
                    invoice = each_payment.reconciled_invoice_ids[0]
                    partner_bank_id = invoice and invoice.partner_bank_id
                if each_payment.reconciled_bills_count > 0 and each_payment.reconciled_bill_ids:
                    bill = each_payment.reconciled_bill_ids[0]
                    partner_bank_id = bill and bill.partner_bank_id
                if not partner_bank_id:
                    partner_bank_id = each_payment.partner_bank_acc_id
                if partner_bank_id:
                    account_numbers.append(partner_bank_id.acc_number)

            final_numbers = []
            for char in [' ', '-']:
                account_numbers = [each_account_number.replace(char, '') for each_account_number in account_numbers]
            for account in account_numbers:
                if len(account) > 14:
                    if len(account) == 17:
                        stripped_ac = ''
                        for i in range(len(account)):
                            if i != 6:
                                stripped_ac += account[i]
                        final_numbers.append(stripped_ac)
                    else:
                        final_numbers.append(account)
            hash_total = sum([int(each_account_number[2:13]) for each_account_number in final_numbers])
            if len(str(hash_total)) > 11:
                hash_total = str(hash_total)[-11:]
            for account in datas["rows"].keys():
                for record in datas["rows"][account]:
                    for column in range(len(record)):
                        file_data.write(str(record[column]))
                        file_data.write(',')
                    file_data.write("\r\n")
                file_data.write("3")
                file_data.write(',')
                file_data.write(str(amount))
                file_data.write(',')
                file_data.write(str(len(total_amount)))
                file_data.write(',')
                file_data.write(str(hash_total))
                file_data.write(',')
                file_data.write("\r\n")

            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

        if eft_format == 'westpac':
            datas = self.export_westpac_eft_report()
            if datas:
                for each_account in datas["rows"].keys():
                    for each_row_list in datas["rows"][each_account]:
                        for data_column_count in range(len(each_row_list)):
                            file_data.write(str(each_row_list[data_column_count]))
                            file_data.write(',')
                        file_data.write("\r\n")

            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'westpac' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

        if eft_format == 'bnz':
            datas = self.export_bnz_eft_report()
            if datas:
                total_amount = [int(round(each_payment.amount *100)) for each_payment in self.filtered(
                    lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft")] #Added code to remove "." as requested by Ashok.PC.2020416

                # account_numbers = [each_payment.partner_bank_id.acc_number for each_payment in self.filtered(
                #     lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft") if
                #                    each_payment.partner_id.bank_ids]

                account_numbers = []
                for each_payment in self.filtered(lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft"):
                    partner_bank_id = self.env['res.partner.bank']
                    if each_payment.reconciled_invoices_count > 0 and each_payment.reconciled_invoice_ids:
                        invoice = each_payment.reconciled_invoice_ids[0]
                        partner_bank_id = invoice and invoice.partner_bank_id
                    if each_payment.reconciled_bills_count > 0 and each_payment.reconciled_bill_ids:
                        bill = each_payment.reconciled_bill_ids[0]
                        partner_bank_id = bill and bill.partner_bank_id
                    if not partner_bank_id:
                        partner_bank_id = each_payment.partner_bank_acc_id
                    if partner_bank_id:
                        account_numbers.append(partner_bank_id.acc_number)

                for char in [' ', '-']:
                    account_numbers = [each_account_number.replace(char, '') for each_account_number in account_numbers]
                hash_total = sum([int(each_account_number[2:13]) for each_account_number in account_numbers])
                zero = 0
                if len(str(hash_total)) > 11:
                    hash_total = str(hash_total)[-11:]
                elif len(str(hash_total)) < 11:
                    for each_zero in range(11 - len(str(hash_total))):
                        hash_total = str(zero) + str(hash_total)
                for each_account in datas["rows"].keys():
                    for each_row_list in datas["rows"][each_account]:
                        for data_column_count in range(len(each_row_list)):
                            file_data.write(str(each_row_list[data_column_count]))
                            file_data.write(',')
                        file_data.write("\r\n")
                    file_data.write("3")
                    file_data.write(',')
                    file_data.write(str(sum(total_amount)))
                    file_data.write(',')
                    file_data.write(str(len(total_amount)))
                    file_data.write(',')
                    file_data.write(str(hash_total))
                    #file_data.write(',')#Removed as requested by Ashok.PC.2020416
                    file_data.write("\r\n")
            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

    def write_excel_workbook(self, workbook, eft_format):
        if eft_format == 'asb':
            dt_string = datetime.now().strftime("%d%m%Y%H%M%S")
            datas = self.export_asb_eft_report(dt_string)
            for each_account in datas["rows"].keys():
                sheet = workbook.add_worksheet(each_account)
                row = 0
                for each_row_list in datas["rows"][each_account]:
                    for data_column_count in range(len(each_row_list)):
                        sheet.write(row, data_column_count, each_row_list[data_column_count])
                    row = row + 1
            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'asb' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

        if eft_format == 'anz':
            vals = self.export_anz_eft_report()
            total_amount = [each_payment.amount for each_payment in self.filtered(
                lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft")]
            amount = ('%.2f' % sum(total_amount)).replace(".", "")

            account_numbers = [each_payment.partner_bank_id.acc_number for each_payment in self.filtered(
                    lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft") if
                                   each_payment.partner_id.bank_ids]

            final_numbers = []
            for char in [' ', '-']:
                account_numbers = [each_account_number.replace(char, '') for each_account_number in account_numbers]
            for account in account_numbers:
                if len(account) > 14:
                    if len(account) == 17:
                        stripped_ac = ''
                        for i in range(len(account)):
                            if i != 6:
                                stripped_ac += account[i]
                        final_numbers.append(stripped_ac)
                    else:
                        final_numbers.append(account)
            hash_total = sum([int(each_account_number[2:13]) for each_account_number in final_numbers])
            if len(str(hash_total)) > 11:
                hash_total = str(hash_total)[-11:]
            row = 0
            for account in vals["rows"].keys():
                sheet = workbook.add_worksheet(account)
                for record in vals["rows"][account]:
                    for column in range(len(record)):
                        sheet.write(row, column, record[column])
                    row = row + 1
                sheet.write(row, 0, 3)
                sheet.write(row, 1, amount)
                sheet.write(row, 2, len(total_amount))
                sheet.write(row, 3, hash_total)
                row = 0
            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

        if eft_format == 'bnz':
            datas = self.export_bnz_eft_report()
            if datas:
                total_amount = [each_payment.amount for each_payment in self.filtered(
                    lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft")]
                # account_numbers = [each_payment.partner_id.bank_ids[0].acc_number for each_payment in self.filtered(
                #     lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft") if
                #                    each_payment.partner_id.bank_ids]
                account_numbers = [each_payment.partner_bank_id.acc_number for each_payment in self.filtered(
                    lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft") if
                                   each_payment.partner_id.bank_ids]
                for char in [' ', '-']:
                    account_numbers = [each_account_number.replace(char, '') for each_account_number in account_numbers]
                hash_total = sum([int(each_account_number[2:13]) for each_account_number in account_numbers])
                zero = 0
                if len(str(hash_total)) > 11:
                    hash_total = str(hash_total)[-11:]
                elif len(str(hash_total)) < 11:
                    for each_zero in range(11 - len(str(hash_total))):
                        hash_total = str(zero) + str(hash_total)
                row = 0
                for each_account in datas["rows"].keys():
                    sheet = workbook.add_worksheet(each_account)
                    for each_row_list in datas["rows"][each_account]:
                        for data_column_count in range(len(each_row_list)):
                            sheet.write(row, data_column_count, each_row_list[data_column_count])
                        row = row + 1
                    sheet.write(row, 0, 3)
                    sheet.write(row, 1, sum(total_amount))
                    sheet.write(row, 2, len(total_amount))
                    sheet.write(row, 3, hash_total)
                    row = 0
            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

        if eft_format == 'westpac':
            datas = self.export_westpac_eft_report()
            if datas:
                row = 0
                for each_account in datas["rows"].keys():
                    sheet = workbook.add_worksheet(each_account)
                    for each_row_list in datas["rows"][each_account]:
                        for data_column_count in range(len(each_row_list)):
                            sheet.write(row, data_column_count, each_row_list[data_column_count])
                        row = row + 1
                    row = 0
            for each_payment_record in self.filtered(
                    lambda p: p.journal_id.eft_format == 'westpac' and p.payment_method_line_id.code == "eft"):
                each_payment_record.update({
                    'status_eft': 'true',
                    'log_ids': [(0, 0, {'created_date': fields.Datetime.now(), 'payment_id': each_payment_record})]
                })

    def action_validate_invoice_payment(self):
        res = super(AccountPayment, self).action_validate_invoice_payment()
        open_invoices = self.env['account.invoice'].browse(self._context.get('active_ids'))
        flag = open_invoices.filtered(lambda inv: inv.type in ['in_refund', 'in_invoice'])
        if flag:
            if len(open_invoices.filtered(lambda inv: inv.partner_id.bank_ids and inv.partner_id.bank_ids[0].acc_number)
                   ) == 0:
                raise UserError(_("Kindly Configure Vendor's Bank Account Details."))
        return res

    def export_westpac_eft_report(self):
        westpac_datas = {}
        index = 1
        for payment in self.filtered(lambda p:
                                     p.journal_id.eft_format == 'westpac' and p.payment_method_line_id.code == "eft"):
            # partner_bank_westpac = self.env['res.partner.bank'].search([
            #     ('partner_id', 'parent_of', [payment.partner_id.id]),
            #     ('state', '=', 'authorised')
            # ])
            partner_bank_westpac = self.env['res.partner.bank']
            if payment.reconciled_invoices_count > 0 and payment.reconciled_invoice_ids:
                invoice = payment.reconciled_invoice_ids[0]
                partner_bank_westpac = invoice and invoice.partner_bank_id
            if payment.reconciled_bills_count > 0 and payment.reconciled_bill_ids:
                bill = payment.reconciled_bill_ids[0]
                partner_bank_westpac = bill and bill.partner_bank_id
            if not partner_bank_westpac:
                partner_bank_westpac = payment.partner_bank_acc_id

            if partner_bank_westpac:
                partner_bank_westpac = partner_bank_westpac[0]
                partner_acc_westpac = partner_bank_westpac.acc_number

                # Replaces space or dash from account number
                for char in [' ', '-']:
                    partner_acc_westpac = partner_acc_westpac.replace(char, '')

                if not partner_bank_westpac.originating_bank:
                    partner_bank_westpac.originating_bank = "0"
                if not partner_bank_westpac.originating_bank_branch:
                    partner_bank_westpac.originating_bank_branch = "0"
                key = payment.journal_id.bank_acc_number
                transaction_code = 00
                mts_source = ''
                if payment.payment_type == 'inbound':
                    transaction_code = 00
                    mts_source = "DD"
                elif payment.payment_type == 'outbound':
                    transaction_code = 50
                    mts_source = "DC"
                if key not in westpac_datas:
                    index = 1
                    westpac_datas.update({key: []})
                    westpac_datas[key].append(
                        ['A', '%0*d' % (6, index), '%0*d' % (2, int(payment.journal_id.bank_id.originating_bank)),
                         '%0*d' % (4, int(payment.journal_id.bank_id.originating_bank_branch)), payment.partner_id.name,
                         payment.partner_id.phone or payment.partner_id.mobile or ' ', ' ',
                         datetime.now().strftime('%d%m%y'), ' '])
                    index += 1
                    westpac_datas[key].append([
                        'D', '%0*d' % (6, index), '%0*d' % (2, int(partner_bank_westpac.originating_bank)),
                             '%0*d' % (4, int(partner_bank_westpac.originating_bank_branch)),
                             partner_acc_westpac or ' ', '0000', transaction_code, mts_source,
                        payment.amount, payment.partner_id.name, partner_bank_westpac.particulars or ' ',
                             partner_bank_westpac.analysis or ' ', partner_bank_westpac.reference or ' ',
                             '%0*d' % (2, int(payment.journal_id.bank_id.originating_bank)),
                             '%0*d' % (4, int(payment.journal_id.bank_id.originating_bank_branch)),
                        key, '0000', payment.company_id.name, ' '
                    ])
                elif key in westpac_datas:
                    westpac_datas[key].append([
                        'D', '%0*d' % (6, index), '%0*d' % (2, int(partner_bank_westpac.originating_bank)),
                             '%0*d' % (4, int(partner_bank_westpac.originating_bank_branch)), partner_acc_westpac or ' ',
                        '0000', transaction_code, mts_source, payment.amount, payment.partner_id.name,
                        partner_bank_westpac.particulars, partner_bank_westpac.analysis, partner_bank_westpac.reference,
                             '%0*d' % (2, int(payment.journal_id.bank_id.originating_bank)),
                             '%0*d' % (4, int(payment.journal_id.bank_id.originating_bank_branch)),
                        key, '0000', payment.company_id.name, ' '])
                index = index + 1
        return {'rows': westpac_datas}

    def export_bnz_eft_report(self):
        bnz_datas = {}
        for payment in self.filtered(lambda p: p.journal_id.eft_format == 'bnz' and p.payment_method_line_id.code == "eft"):
            key = payment.journal_id.bank_acc_number
            # partner_bank_bnz = self.env['res.partner.bank'].search([
            #     ('partner_id', 'parent_of', [payment.partner_id.id]),
            #     ('state', '=', 'authorised')
            # ])
            # partner_bank_bnz = payment.partner_bank_acc_id

            partner_bank_bnz = self.env['res.partner.bank']
            if payment.reconciled_invoices_count > 0 and payment.reconciled_invoice_ids:
                invoice = payment.reconciled_invoice_ids[0]
                partner_bank_bnz = invoice and invoice.partner_bank_id
            if payment.reconciled_bills_count > 0 and payment.reconciled_bill_ids:
                bill = payment.reconciled_bill_ids[0]
                partner_bank_bnz = bill and bill.partner_bank_id
            if not partner_bank_bnz:
                partner_bank_bnz = payment.partner_bank_acc_id
            if partner_bank_bnz:
                partner_bank_bnz = partner_bank_bnz[0]
                # partner_acc_bnz = payment.partner_bank_acc_id and payment.partner_bank_acc_id.acc_number
                partner_acc_bnz = partner_bank_bnz.acc_number
                partner_particulars_bnz = partner_bank_bnz.particulars
                partner_reference_bnz = partner_bank_bnz.reference
                partner_analysis_bnz = partner_bank_bnz.analysis
                if partner_particulars_bnz:
                    partner_particulars_bnz=partner_particulars_bnz.strip() #PC.20200417
                if partner_reference_bnz:
                    partner_reference_bnz = partner_reference_bnz.strip()
                if partner_analysis_bnz:
                    partner_analysis_bnz = partner_analysis_bnz.strip()

                # Replaces space or dash from account number
                for char in [' ', '-']:
                    partner_acc_bnz = partner_acc_bnz.replace(char, '')

                if bnz_datas.get(key):
                    # bnz_datas[key].append([
                    #     2, partner_acc_bnz, payment.journal_id.bnz_transaction_code, payment.amount,
                    #     payment.partner_id.name, payment.partner_id.ref or ' ', ' ', ' ', ' ',
                    #     payment.company_id.name, ' ', ' ', ' '])
                    #Changed the above code as below as asked by Ashok.PC.20200416
                    bnz_datas[key].append([
                        2, partner_acc_bnz, payment.journal_id.bnz_transaction_code, int(round(payment.amount*100)),
                        payment.partner_id.name, partner_reference_bnz or ' ', partner_particulars_bnz or ' ', '',
                        partner_analysis_bnz, partner_particulars_bnz or ' ', ' ','',])
                else:
                    nz=timezone("NZ")
                    bnz_datas.update({key: []})
                    # bnz_datas[key].append([1, ' ', ' ', ' ', payment.journal_id.bank_acc_number, 7,
                    #                        datetime.now().strftime('%y%m%d'),
                    #                        datetime.now().strftime('%y%m%d'),
                    #                        payment.journal_id.bulk_individual_indicator])
                    bnz_datas[key].append([1, '', '', '', payment.journal_id.bank_acc_number.replace(' ', '').replace('-', ''), 7,
                                           datetime.now().astimezone(nz).strftime('%y%m%d'),
                                           datetime.now().astimezone(nz).strftime('%y%m%d')]) #Removed payment.journal_id.bulk_individual_indicator as asked by Ashok.PC.20200416
                                                                                          #Ryan: re-added bulk indicator - it's possible to set it to *blank* value via UI config page
                                                                                          # Nirali: Removed payment.journal_id.bulk_individual_indicator - requested by Ashok
                    # bnz_datas[key].append([
                    #     2, partner_acc_bnz, payment.journal_id.bnz_transaction_code, payment.amount,
                    #     payment.partner_id.name, payment.partner_id.ref or ' ', ' ', ' ', ' ',
                    #     payment.company_id.name, ' ', ' ', ' '])
                    #Changed the above code as below as asked by Ashok.PC.20200416
                    bnz_datas[key].append([
                        2, partner_acc_bnz, payment.journal_id.bnz_transaction_code, int(round(payment.amount*100)),
                        payment.partner_id.name, partner_reference_bnz or ' ', partner_particulars_bnz or ' ', '',
                        partner_analysis_bnz, partner_particulars_bnz or ' ', ' ','',])
        return {'rows': bnz_datas}

    def export_anz_eft_report(self):
        datas = {}
        for payment in self.filtered(lambda p: p.journal_id.eft_format == 'anz' and p.payment_method_line_id.code == "eft"):
            transaction_code = ''
            if payment.payment_type == 'inbound':
                transaction_code = 00
            elif payment.payment_type == 'outbound':
                transaction_code = 50
            key = payment.journal_id.bank_acc_number
            # partner_banks = payment.partner_id.bank_ids or payment.partner_id.parent_id.bank_ids
            # partner_bank_anz = partner_banks.filtered(lambda each: each.state == 'authorised')
            # partner_bank_anz = self.env['res.partner.bank'].search([
            #     ('partner_id', 'parent_of', [payment.partner_id.id]),
            #     ('state', '=', 'authorised')
            # ])
            partner_bank_anz = self.env['res.partner.bank']
            if payment.reconciled_invoices_count > 0 and payment.reconciled_invoice_ids:
                invoice = payment.reconciled_invoice_ids[0]
                partner_bank_anz = invoice and invoice.partner_bank_id
            if payment.reconciled_bills_count > 0 and payment.reconciled_bill_ids:
                bill = payment.reconciled_bill_ids[0]
                partner_bank_anz = bill and bill.partner_bank_id
            if not partner_bank_anz:
                partner_bank_anz = payment.partner_bank_acc_id

            amount = ('%.2f' % payment.amount).replace(".", "")
            if partner_bank_anz:
                partner_bank_anz = partner_bank_anz[0]
                # partner_acc_anz = payment.partner_bank_acc_id and payment.partner_bank_acc_id.acc_number
                partner_acc_anz = partner_bank_anz.acc_number

                # Replaces space or dash from account number
                for char in [' ', '-']:
                    partner_acc_anz = partner_acc_anz.replace(char, '')

                partner_particulars_anz = partner_bank_anz.particulars
                partner_analysis_anz = partner_bank_anz.analysis
                partner_ref_anz = partner_bank_anz.reference
                if datas.get(key):
                    datas[key].append([
                        2,
                        partner_acc_anz or '', transaction_code or '', amount, payment.partner_id.name,
                        partner_ref_anz or '', partner_analysis_anz or '', payment.company_id.name,
                        partner_particulars_anz or '', '', partner_analysis_anz or '', partner_ref_anz or '',
                        partner_particulars_anz or ''])
                else:
                    batch_create_date = datetime.now().strftime('%Y%m%d')
                    datas.update({key: []})
                    datas[key].append([1, '', '', '', '', '', batch_create_date, batch_create_date])
                    datas[key].append([
                        2,
                        partner_acc_anz or '', transaction_code or '', amount, payment.partner_id.name,
                        partner_ref_anz or '', partner_analysis_anz or '', payment.company_id.name,
                        partner_particulars_anz or '', '', partner_analysis_anz or '', partner_ref_anz or '',
                        partner_particulars_anz or ''])
        return {'rows': datas}

    def export_asb_eft_report(self, dt_string):
        datas = {}
        for payment in self.filtered(lambda p: p.journal_id.eft_format == 'asb' and p.payment_method_line_id.code == "eft"):
            key = payment.journal_id.bank_acc_number

            asb_date = payment.date
            year_asb, month_asb, day_asb = asb_date.strftime("%Y,%m,%d").split(',')
            date_format_asb = day_asb + '/' + month_asb + '/' + year_asb
            deduction_acc = payment.journal_id.bank_acc_number
            # Replaces space or dash from account number
            for char in [' ', '-']:
                deduction_acc = deduction_acc.replace(char, '')

            deduction_acc = \
                deduction_acc[0:2] + '-' + deduction_acc[2:6] + '-' + deduction_acc[6:13] + '-' + deduction_acc[13:16]

            # partner_bank_asb = self.env['res.partner.bank'].search([
            #     ('partner_id', 'parent_of', [payment.partner_id.id]),
            #     ('state', '=', 'authorised')
            # ])
            # partner_bank_asb = payment.partner_bank_acc_id

            partner_bank_asb = self.env['res.partner.bank']
            if payment.reconciled_invoices_count > 0 and payment.reconciled_invoice_ids:
                invoice = payment.reconciled_invoice_ids[0]
                partner_bank_asb = invoice and invoice.partner_bank_id
            if payment.reconciled_bills_count > 0 and payment.reconciled_bill_ids:
                bill = payment.reconciled_bill_ids[0]
                partner_bank_asb = bill and bill.partner_bank_id
            if not partner_bank_asb:
                partner_bank_asb = payment.partner_bank_acc_id

            if partner_bank_asb:
                partner_bank_asb = partner_bank_asb[0]
                partner_acc_asb = partner_bank_asb.acc_number
                partner_particulars_asb = partner_bank_asb.particulars
                partner_analysis_asb = partner_bank_asb.analysis
                partner_ref_asb = partner_bank_asb.reference

                payee_particular = partner_particulars_asb
                payee_code = partner_analysis_asb
                payee_ref = partner_ref_asb
                destination_acc = partner_acc_asb
                payer_particular = partner_particulars_asb
                payer_code = partner_analysis_asb
                payer_ref = partner_ref_asb
                payer_name = payment.partner_id.name

                if not payee_particular:
                    payee_particular = ''
                if not payee_code:
                    payee_code = ''
                if not payee_ref:
                    payee_ref = ''
                if not payer_particular:
                    payer_particular = ''
                if not payer_code:
                    payer_code = ''
                if not payer_ref:
                    payer_ref = ''
                #Update Memo(communication) field of the payment.PC.20201012
                communication=  "-".join((payment.ref, dt_string))
                payment.write({'ref':communication,'payment_reference':dt_string})

                if datas.get(key):
                    datas[key].append([dt_string, date_format_asb, deduction_acc, payment.amount, payee_particular,
                                       payee_code, payee_ref, destination_acc, payer_particular, payer_code,
                                       payer_ref, payer_name])
                else:
                    datas.update({key: []})
                    datas[key].append([dt_string, date_format_asb, deduction_acc, payment.amount, payee_particular,
                                       payee_code, payee_ref, destination_acc, payer_particular, payer_code,
                                       payer_ref, payer_name])
        return {'rows': datas, 'filename': str(datetime.now()) + '_asb'}


    def eft_directdebit_export(self, report_format, eft_format, duedate):
        """
        Generate a direct debit EFT file for all moves in @self, using report type @report_type (text or xlsx),
        for bank @eft_format.

        This function should return a tuple (headers, data):
        - headers: headers, including at least content-length, -type, and -disposition
        - data: a byte[] array containing the file data (e.g. BytesIO/StringIO .read()/.getvalue())

        This function calls eft_directdebit_export_<bank> to get the raw EFT data, which should be a 2d list, like:
        [
            [row1_col1, row1_col2, ...],
            [row2_col1, row2_col2, row2_col3, ...],
            ...
        ]

        Blank ("") values are allowed in this 2d list, and will result in empty cells, or double-comma for CSV.
        The returned list should include *ALL* data necessary for the EFT file, e.g., including headers, footers, 
        hashes, etc etc. Rows in the array may be of different lengths
        """

        # get the raw data (2d list)
        if eft_format == 'bnz':
            data_raw = self.eft_directdebit_export_bnz(duedate)
        elif eft_format == 'anz':
            data_raw = self.eft_directdebit_export_anz(duedate)
        else:
            raise UserError("Warning: Unknown EFT format chosen for direct debit export")

        # convert to appropriate format
        if report_format == 'xlsx':
            stream = BytesIO()

            workbook = xlsxwriter.Workbook(stream)
            sheet = workbook.add_worksheet('directdebit')

            for row, rowdata in enumerate(data_raw):
                for col, celldata in enumerate(rowdata):
                    sheet.write(row, col, celldata)

            workbook.close()
            stream.seek(0) 
            tz_nz = timezone("NZ")
            disposition = content_disposition(eft_format.capitalize() + '_' + datetime.now().astimezone(tz_nz).strftime('%Y-%m-%d') + '.xlsx')

            data = stream.getvalue()
            headers = [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Length', len(data)),
                ('Content-Disposition', disposition),
            ]
        elif report_format == 'text':
            stream = StringIO()

            for row, rowdata in enumerate(data_raw):
                for col, celldata in enumerate(rowdata):
                    stream.write(str(celldata))

                    if col < (len(rowdata) - 1):
                        stream.write(',')

                stream.write('\r\n')

            stream.seek(0)
            tz_nz = timezone("NZ")
            disposition = content_disposition(eft_format.capitalize() + '_' + datetime.now().astimezone(tz_nz).strftime('%Y-%m-%d') + '.txt')

            data = stream.read()
            headers = [
                ('Content-Type', 'text/csv'),
                ('Content-Length', len(data)),
                ('Content-Disposition', disposition),
            ]
        else:
            raise UserError("Warning: Unknown EFT file type chosen for direct debit export")

        return (headers, data)

    def eft_directdebit_export_bnz(self, duedate):
        """
        EFT format info can be found here:
        https://www.bnz.co.nz/assets/business-banking-help-support/internet-banking/ib4b-file-format-guide.pdf?3295ba2d65937d36051f4e5fa0e9694ea5683c2b
        """

        # EFT lines will be stored here, as a 2d array/list
        eftdata = []

        tz_nz = timezone('NZ')
        strftime_format = '%y%m%d'

        # get the account number, and sanitise
        journal_id = self.journal_id
        account_number = journal_id.bank_account_id.acc_number.replace('-', '').replace(' ', '')

        # add header record (p15 in the format doc)
        eftdata.append([
            '1',
            journal_id.bnz_directdebit_authority,
            '',
            '',
            account_number,
            '6',
            duedate,
            fields.Datetime.now().astimezone(tz_nz).strftime(strftime_format),
            journal_id.bulk_individual_indicator
        ])

        trans_count = 0
        trans_total = 0
        trans_hash = 0
        
        # add payment lines (p16)
        for payment in self:
            # get and parse customer bank account
            # partner_bank_id = self.env['res.partner.bank'].search([
            #     ('partner_id', 'parent_of', [payment.partner_id.id]),
            #     ('state', '=', 'authorised')
            # ])
            # partner_bank_id = payment.partner_bank_acc_id
            
            partner_bank_id = self.env['res.partner.bank']
            if payment.reconciled_invoices_count > 0 and payment.reconciled_invoice_ids:
                invoice = payment.reconciled_invoice_ids[0]
                partner_bank_id = invoice and invoice.partner_bank_id
            if payment.reconciled_bills_count > 0 and payment.reconciled_bill_ids:
                bill = payment.reconciled_bill_ids[0]
                partner_bank_id = bill and bill.partner_bank_id
            if not partner_bank_id:
                partner_bank_id = payment.partner_bank_acc_id
            
            bank_account = partner_bank_id.acc_number.replace('-', '').replace(' ', '')

            # convert payment amount to cents
            # amount_cents = int(float_round(payment.amount * 100, precision_digits=0.01))
            amount_cents = int(float_round(payment.amount * 100, precision_digits=0.00))

            # get reference, where the string is trimmed from the LEFT side to make it
            # 12 chars at most. trimmed from the left because the useful info (e.g. SO
            # number) will probably be on the right-hand side
            reference = payment.ref[max(len(payment.ref) - 12, 0):]

            # calculate transaction hash
            account_for_hash = int(bank_account[2:13])

            # track totals for control record
            trans_total += amount_cents
            trans_count += 1
            trans_hash += account_for_hash

            eftdata.append([
                '2',
                bank_account,
                '00',
                amount_cents,
                payment.partner_id.name,
                reference,
                payment.company_id.name,
                '',
                reference,
                payment.company_id.name,
                payment.company_id.name,
                reference,
                '',
            ])

        # add control row
        eftdata.append([
            '3',
            trans_total,
            trans_count,
            str(trans_hash)[-11:].zfill(11)
        ])

        return eftdata

    def eft_directdebit_export_anz(self, duedate):
        # EFT lines will be stored here, as a 2d array/list
        eftdata = []

        tz_nz = timezone('NZ')
        strftime_format = '%Y%m%d'

        # get the account number, and sanitise
        journal_id = self.journal_id
        account_number = journal_id.bank_account_id.acc_number.replace('-', '').replace(' ', '')

        # add header record (p15 in the format doc)
        eftdata.append([
            '1',
            '',
            '',
            '',
            '',
            '',
            fields.Datetime.now().astimezone(tz_nz).strftime(strftime_format),
            fields.Datetime.now().astimezone(tz_nz).strftime(strftime_format),
            '',
        ])

        trans_count = 0
        trans_total = 0
        trans_hash = 0

        # add payment lines (p16)
        for payment in self:
            # get and parse customer bank account
            # partner_bank_id = self.env['res.partner.bank'].search([
            #     ('partner_id', 'parent_of', [payment.partner_id.id]),
            #     ('state', '=', 'authorised')
            # ])
            # partner_bank_id = payment.partner_bank_acc_id

            partner_bank_id = self.env['res.partner.bank']
            if payment.reconciled_invoices_count > 0 and payment.reconciled_invoice_ids:
                invoice = payment.reconciled_invoice_ids[0]
                partner_bank_id = invoice and invoice.partner_bank_id
            if payment.reconciled_bills_count > 0 and payment.reconciled_bill_ids:
                bill = payment.reconciled_bill_ids[0]
                partner_bank_id = bill and bill.partner_bank_id
            if not partner_bank_id:
                partner_bank_id = payment.partner_bank_acc_id

            bank_account = (partner_bank_id and partner_bank_id.acc_number) and partner_bank_id.acc_number.replace('-', '').replace(' ', '') or ''
            partner_particulars = partner_bank_id and partner_bank_id.particulars or ''
            partner_reference = partner_bank_id and partner_bank_id.reference or ''
            partner_analysis = partner_bank_id and partner_bank_id.analysis or ''

            # convert payment amount to cents
            amount_cents = int(float_round(payment.amount * 100, precision_digits=0.00))

            # get reference, where the string is trimmed from the LEFT side to make it
            # 12 chars at most. trimmed from the left because the useful info (e.g. SO
            # number) will probably be on the right-hand side
            reference = payment.ref[max(len(payment.ref) - 12, 0):]

            # calculate transaction hash
            account_for_hash = bank_account and int(bank_account[2:13]) or 0

            # track totals for control record
            trans_total += amount_cents
            trans_count += 1
            trans_hash += account_for_hash

            eftdata.append([
                '2',
                bank_account,
                '00',
                amount_cents,
                payment.partner_id.name,
                partner_reference,
                partner_analysis,
                '',
                partner_particulars,
                'ANZ BANK',
                partner_particulars,
                partner_reference,
                partner_analysis,
            ])

        # add control row
        eftdata.append([
            '3',
            trans_total,
            trans_count,
            str(trans_hash)[-11:].zfill(11)
        ])

        return eftdata


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    eft_format = fields.Selection([('anz', 'ANZ'), ('asb', 'ASB'), ('bnz', 'BNZ'), ('kiwi', 'KIWI BANK'),
                                   ('westpac', 'WESTPAC')], string='Bank EFT Format')

    bulk_individual_indicator = fields.Selection([
        (' ', ' '), ('C', 'C'), ('I', 'I'), ('O', 'O')], string="Bulk or Individual Listing Indicator",
        help="Blank = Bulk listing.\nC = Individual listing, details copied from other party.\nI = Individual listing, "
             "payer’s and other party’s details entered individually.\nO = Individual listing, payer’s details all the "
             "same.")
    bnz_transaction_code = fields.Selection([
        ('50', '50'), ('52', '52'), ('61', '61')], help="50 and 61 = Standard Credit.\n52 = Payroll.", default='50')
    bnz_directdebit_authority = fields.Char(string='BNZ Direct Debit Authority', help='Direct debit \'authority\' number given to you by BNZ. Note this is mandatory for direct debit EFT file exporting.')
    originating_bank = fields.Char(related="bank_id.originating_bank", string="Originating Bank")
    originating_bank_branch = fields.Char(related="bank_id.originating_bank_branch", string="Originating Branch")
    anz_trace_bsb_number = fields.Char(
        string="Trace BSB Number", size=7)
    anz_trace_account_number = fields.Char(
        string="Trace Account Number", size=9)
    anz_identification_number = fields.Integer(string="User ID", size=6)
    anz_notes = fields.Char(string="Description", size=12)

    @api.model
    def create(self, vals):
        res = super(AccountJournal, self).create(vals)
        originating_bank, originating_bank_branch = '', ''
        if vals:
            if 'originating_bank' in vals:
                originating_bank = vals['originating_bank']
            if 'originating_bank_branch' in vals:
                originating_bank_branch = vals['originating_bank_branch']
            if originating_bank and originating_bank_branch:
                if len(originating_bank) > 2:
                    raise UserError(_("For Westpac Bank Account Bank Code Must 2 Digits Long Only!!"))
                if len(originating_bank_branch) > 4:
                    raise UserError(_("For Westpac Bank Account Bank Branch Code Must 4 Digits Long Only!!"))

        if 'eft_format' in vals:
            if vals['eft_format']:
                if 'bank_acc_number' in vals:
                    acc_no = vals['bank_acc_number'] or ''
                    if acc_no:
                        acc_no = re.sub(r'-', "", acc_no)
                        acc_no = re.sub(r' ', "", acc_no)
                    if acc_no and not acc_no.isdigit():
                        raise UserError(
                            _('Bank account and credit card numbers should be numerical.'))
                    length_acc = len(acc_no)
                    if vals['eft_format'] == 'bnz':
                        if length_acc not in [15, 16]:
                            raise UserError(
                                _('BNZ domestic account and credit card numbers should be 15 or 16 digits long.'))
                    elif vals['eft_format'] == 'asb':
                        if length_acc not in [15, 16, 19]:
                            raise UserError(
                                _('ASB domestic account and credit card numbers should be 15 or 16 or 19 digits long.'))
                    elif vals['eft_format'] == 'westpac':
                        if length_acc != 8:
                            raise UserError(
                                _('WESTPAC domestic account and credit card numbers must be 8 digits long.'))
                    elif vals['eft_format'] in ['bnz', 'asb', ]:
                        if length_acc < 15:
                            raise UserError(
                                _('Bank account and credit card numbers should be more than 15 digits long.'))
        return res

    def write(self, vals):
        res = super(AccountJournal, self).write(vals)
        for record in self:
            if record.type != 'bank':
                continue

            if 'originating_bank' in vals:
                originating_bank = vals['originating_bank']
                if originating_bank:
                    if len(originating_bank) > 2:
                        raise UserError(_("For Westpac Bank Account Bank Code Must 2 Digits Long Only!!"))
            if 'originating_bank_branch' in vals:
                originating_bank_branch = vals['originating_bank_branch']
                if originating_bank_branch:
                    if len(originating_bank_branch) > 4:
                        raise UserError(_("For Westpac Bank Account Bank Branch Code Must 4 Digits Long Only!!"))
            if 'bank_acc_number' in vals:
                acc_no = vals['bank_acc_number']
            else:
                acc_no = record.bank_acc_number
            if acc_no:
                acc_no = re.sub(r'-', "", acc_no)
                acc_no = re.sub(r' ', "", acc_no)
            if acc_no and not acc_no.isdigit():
                raise UserError(
                    _('Bank account and credit card numbers should be numerical.'))
            if 'eft_format' in vals:
                format_eft = vals['eft_format']
            else:
                format_eft = record.eft_format
            if format_eft:
                length_acc = len(acc_no)
                if format_eft == 'bnz':
                    if length_acc not in [15, 16]:
                        raise UserError(
                            _('BNZ domestic account and credit card numbers should be 15 or 16 digits long.'))
                elif format_eft == 'asb':
                    if length_acc not in [15, 16, 19]:
                        raise UserError(
                            _('ASB domestic account and credit card numbers should be 15 or 16 or 19 digits long.'))
                elif format_eft == 'westpac':
                    if length_acc != 8:
                        raise UserError(
                            _('WESTPAC domestic account and credit card numbers must be 8 digits long.'))
                elif format_eft in ['bnz', 'asb', ]:
                    if length_acc < 15:
                        raise UserError(
                            _('Bank account and credit card numbers should be more than 15 digits long.'))
        return res

    def _eft_directdebit_issue(self):
        """
        Check the journal to ensure it is suitably configured for directdebit payments

        Return False if things are fine, or an error message if things are misconfigured.

        Remember that the message is shown after clicking 'Create Payments' on the invoice
        wizard, so it's probably pertinent to include a note that this error came from
        the journal configuration.
        """
        self.ensure_one()

        if self.eft_format == 'bnz':
            if self.bnz_directdebit_authority and len(self.bnz_directdebit_authority) > 0:
                return False
            else:
                return 'The journal is not correctly configured for BNZ direct deibt. Ensure you have entered the BNZ direct debit \'authority\' number on your Bank journal'
        else:
            return False

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    is_directdebit = fields.Boolean(string='Is Direct Debit', default=False, help='Is this a payment term where money will be direct-debited from the customer?')

class ResBank(models.Model):
    _inherit = 'res.bank'

    originating_bank = fields.Char(string="Originating Bank")
    originating_bank_branch = fields.Char(string="Originating Branch")
    eft_format = fields.Selection([('anz', 'ANZ'), ('asb', 'ASB'), ('bnz', 'BNZ'), ('kiwi', 'KIWI BANK'),
                                   ('westpac', 'WESTPAC')], string='Bank EFT Format')

    @api.constrains('bic')
    def check_eft_format(self):
        if self.eft_format == 'anz' and len(self.bic) > 7:
            raise UserError(
                _('Bank Identifier code for ANZ format must be 7 digits long only!'))


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _inherit = ['res.partner.bank', 'mail.thread', 'mail.activity.mixin', 'portal.mixin']

    originating_bank = fields.Char(string="Originating Bank", tracking=True)
    originating_bank_branch = fields.Char(string="Originating Branch", tracking=True)
    acc_number = fields.Char('Account Number', tracking=True, required=True)
    analysis = fields.Char(string='Analysis', tracking=True, required=True)
    particulars = fields.Char(string='Particulars', tracking=True, required=True)
    reference = fields.Char(string='Reference', tracking=True,required=True)
    state = fields.Selection([
        ('new', 'New'), ('authorised', 'Authorized')], string='Status', default="new", tracking=True)
    bank_id = fields.Many2one(tracking=True)
    authorized_by = fields.Many2one('res.users', string="Authorized By")
    authorized_date = fields.Datetime(string="Authorization Date")
    updated_by = fields.Many2one('res.users', string="Updated By", help="This is a User who have updated Account Number of this record.")

    def authorise_bank(self):

        if self.create_uid.id == self.env.user.id and self.env.user.id != SUPERUSER_ID:
            raise UserError(
                _("Bank Account Created user cannot Authorise the same Bank"))
        if self.updated_by and self.updated_by.id == self.env.user.id and self.env.user.id != SUPERUSER_ID:
            raise UserError(
                _("Bank Account Updated By user cannot Authorise the same Bank"))

        self.sudo().write({'state': 'authorised',
                           'authorized_by': self.env.user.id,
                           'authorized_date': datetime.now()
                           })
        self.env['mail.message'].sudo().create({
            'model': 'res.partner.bank',
            'res_id': self.id,
            'message_type': 'notification',
            'body':  _('Bank authorized.'),
            'author_id': self.env.user.partner_id.id
        })

    @api.model
    def create(self, vals):
        res = super(ResPartnerBank, self).create(vals)
        acc_no = vals['acc_number']
        acc_no = re.sub(r'-', "", acc_no)
        acc_no = re.sub(r' ', "", acc_no)
        if not acc_no.isdigit():
            raise UserError(
                _('Bank account and credit card numbers should be numerical.'))
        return res

    def write(self, vals):
        if 'acc_number' in vals:
            vals.update({'state': 'new', 'updated_by': self.env.user.id})
        res = super(ResPartnerBank, self).write(vals)
        if 'acc_number' in vals:
            acc_no = vals['acc_number']
        else:
            acc_no = self.acc_number
        acc_no = re.sub(r'-', "", acc_no)
        acc_no = re.sub(r' ', "", acc_no)
        if not acc_no.isdigit():
            raise UserError(
                _('Bank account and credit card numbers should be numerical.'))
        return res
