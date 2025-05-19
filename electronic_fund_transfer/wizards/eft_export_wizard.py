# -*- coding: utf-8 -*-


from odoo import models, fields, api
from odoo.exceptions import UserError


class PaymentEftFormatSelectionWizard(models.TransientModel):
    _name = 'payment.eft.format.selection.wizard'
    _description = "EFT File Format Selection Wizard"

    eft_format = fields.Selection([('anz', 'ANZ'), ('asb', 'ASB'), ('bnz', 'BNZ'), ('kiwi', 'KIWI BANK'),
                                   ('westpac', 'WESTPAC')], default="westpac", string='Bank EFT Format')
    report_format = fields.Selection([('text', 'Text'), ('xlsx', 'XLSX')], default="text", string='Report Format')
    eft_type = fields.Selection(string='Type', selection=[('norm', 'Normal EFT'), ('dd', 'Direct Debit')], readonly=True)

    def action_download_excel_file(self):
        payments = self.env['account.payment'].browse(self._context.get('active_ids', False))
        string_payment = ''
        for payment in payments:
            string_payment = string_payment + str(payment.id) + ','
        if payments:
            if self.eft_type == 'norm':
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/report/download/xlsx/%s/%s/%s' % (string_payment, self.eft_format, self.report_format),
                    'target': 'new'
                }
            elif self.eft_type == 'dd':
                dates = payments.mapped('date')
                all_same = all(v == dates[0] for v in dates)

                if not all_same:
                    raise UserError("Warning! Payment dates are inconsistent. The direct debit file will debit for ALL payments on the same date. Please only select payments with the same \'Date\'.")

                date = dates[0]
                date_string = "%s%s%s" % (str(date.year)[-2:].zfill(2), str(date.month).zfill(2), str(date.day).zfill(2))
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/report/download/directdebit-eft/%s/%s/%s?duedate=%s' % (self.report_format, self.eft_format, ",".join(str(p.id) for p in payments), date_string),
                    'target': 'new'
                }
        else:
            return {
                'type': 'ir.actions.act_window_close',
            }

    @api.model
    def default_get(self, fields_list):
        res = super(PaymentEftFormatSelectionWizard, self).default_get(fields_list)
        payments = self.env['account.payment'].browse(self._context.get('active_ids', False))

        if 'eft_format' in fields_list:
            journal_id = payments.journal_id

            if journal_id:
                bank_id = journal_id.bank_id

            if bank_id:
                eft_format = bank_id[0].eft_format

                res.update({
                    'eft_format': eft_format
                })

        if 'eft_type' in fields_list:
            payment_type = payments.mapped('payment_type')

            if payment_type:
                payment_type = payment_type[0]

                if payment_type == 'inbound':
                    eft_type = 'dd'
                elif payment_type == 'outbound':
                    eft_type = 'norm'

                res.update({
                    'eft_type': eft_type
                })

        return res
