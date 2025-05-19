# -*- coding: utf-8 -*-


from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from pytz import timezone

import logging
_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'


    eft_format = fields.Selection(
        selection=[
            ('anz', 'ANZ'), ('asb', 'ASB'), ('bnz', 'BNZ'),
            ('kiwi', 'KIWI BANK'), ('westpac', 'WESTPAC')
        ],
        string='Bank EFT Format')
    report_format = fields.Selection(
        selection=[('text', 'Text'), ('xlsx', 'XLSX')],
        default="text",
        string='Report Format')

    payment_method_code = fields.Char(readonly=True, related="payment_method_line_id.code")
    has_been_exported = fields.Boolean(readonly=True)
    eft_type = fields.Selection(string='Type', selection=[('norm', 'Normal EFT'), ('dd', 'Direct Debit')], readonly=True)


    def _calculate_debit_date(self):
        """
        Calculate a suitable debit date for the invoices.

        This is the date that all direct debits in the EFT file will be processed, and
        presents some difficulty. Nothing guarantees that *all* invoices will be due
        on the same date, but we can make a few assumptions:
        1. All invoices are using the same payment terms
        2. That payment term is something like "due 20th of the following month"
        3. A filter will be grouping invoice into 'due month'

        These facts together mean that we *can* make a smart guess about the due date.
        As a backup, the field will be editable, so users can set it to whatever they like
        """

        if self.line_ids:
            # term_ids = self.line_ids.move_id.invoice_payment_term_id
            # tz_nz = timezone("NZ")
            # tz_utc = timezone("UTC")
            # date_today = fields.Datetime.now().astimezone(tz_nz)
            # date_month = fields.Datetime.now().astimezone(tz_nz).replace(day=1)
            # suitable_due_date = fields.Datetime.now().astimezone(tz_nz)

            # for term in term_ids:
            #     # exactly 1 'balance' line is required, so this will be a singleton
            #     line = term.line_ids.filtered(lambda l: l.value == 'balance')

            #     # line.days is the field set when option = 'of the following month'
            #     due_day = fields.Datetime.now().astimezone(tz_nz).replace(day=line.days)

            #     if due_day > suitable_due_date:
            #         suitable_due_date = due_day

            # if suitable_due_date.date() <= date_today.date():
            #     suitable_due_date += relativedelta(months=1)

            # return suitable_due_date.date()

            due_dates = self.line_ids.move_id.mapped('invoice_date_due')

            if len(due_dates) >= 1:
                all_same = all(v == due_dates[0] for v in due_dates)

                #raju if not all_same:
                #raju    raise ValidationError("Some invoices have different due dates. When processing a direct debit, ALL invoices will be debited on the same date. Please ensure you only select invoices where the 'Due Date' column is identical. If necessary, you may need to process direct debits in separate batches.")
                
                #raju return due_dates[0]
                return False
            else:
                return False

        return False

    @api.onchange('payment_method_line_id')
    def _compute_date(self):
        for record in self:
            if record.payment_method_line_id.code == 'eft':
                date = record._calculate_debit_date()

                if date:
                    record.payment_date = date
                else:
                    record.payment_date = fields.Date.context_today(self)
            else:
                record.payment_date = fields.Date.context_today(self)

    def action_create_directdebit(self):
        self.ensure_one()
        # ensure all invoices are using the same payment term. this is critical because
        # we can only set one global 'due date' for the directdebit EFT file, so all invoice
        # due dates must be the same. we'll assume the EFT files are being downloaded
        # regularly so we don't end up with any very old invoices
        all_moves = self.line_ids.move_id
        all_terms = all_moves.invoice_payment_term_id
        #raju if len(all_terms) != 1 or not all_terms.is_directdebit:
        #raju    raise UserError('Ensure all selected invocies are using the same payment term, and that it is marked as direct-debit-capable')

        # ensure that we're dealing with a single journal
        all_journals = all_moves.journal_id
        if len(all_journals) != 1:
            raise UserError('The selected invoices are not all using the same journal.')

        # ensure that the journal is properly configured for direct debit  
        err = all_journals._eft_directdebit_issue()
        if err:
            raise UserError(err)

        payments = self._create_payments()
        date_string = "%s%s%s" % (str(self.payment_date.year)[-2:].zfill(2), str(self.payment_date.month).zfill(2), str(self.payment_date.day).zfill(2))

        self.has_been_exported = True
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/download/directdebit-eft/%s/%s/%s?duedate=%s' % (self.report_format, self.eft_format, ",".join(str(p.id) for p in payments), date_string),
            'target': 'new'
        }

    def action_create_eft(self):
        self.ensure_one()

        # ensure that we're dealing with a single journal
        all_moves = self.line_ids.move_id
        message = ""
        for move in all_moves:
            if not move.partner_bank_id or not move.partner_bank_id.authorized_by or not move.partner_bank_id.authorized_by.name:
                message += "Vendor "+move.partner_id.name+": Bank Account not authorised.\n"
        if message:
            raise UserError(message)
        all_journals = all_moves.journal_id
        if len(all_journals) != 1:
            raise UserError('The selected invoices are not all using the same journal.')

        payments = self._create_payments()
        date_string = "%s%s%s" % (str(self.payment_date.year)[-2:].zfill(2), str(self.payment_date.month).zfill(2), str(self.payment_date.day).zfill(2))

        self.has_been_exported = True
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/download/xlsx/%s/%s/%s' % (",".join(str(p.id) for p in payments), self.eft_format, self.report_format),
            'target': 'new'
        }
    
    @api.model
    def default_get(self, fields_list):
        res = super(AccountPaymentRegister, self).default_get(fields_list)

        if 'eft_format' in fields_list:
            journal_id = self.env['account.move']._search_default_journal(['bank'])

            if journal_id:
                bank_id = journal_id.bank_id

            if journal_id.eft_format:
                res.update({
                    'eft_format': journal_id.eft_format
                })
            elif bank_id:
                eft_format = bank_id[0].eft_format

                res.update({
                    'eft_format': eft_format
                })
        if 'eft_type' in fields_list:
            move_ids = self.env['account.move'].browse(self._context.get('active_ids', False))

            move_type = move_ids.mapped('move_type')

            if move_type and len(move_type) > 0:
                # check that all are the same
                if not any([t == move_type[0] for t in move_type]):
                    raise UserError("Warning! You attempted to process a mixture of customer Invoices and vendor Bills. Please register payments for one type at a time only.")
                
                if move_type[0] in ('out_invoice'):
                    eft_type = 'dd'
                elif move_type[0] in ('in_invoice', 'out_refund'):
                    eft_type = 'norm'
                else: eft_type = False

                res.update({
                    'eft_type': eft_type,
                })
        return res
