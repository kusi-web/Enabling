# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    name = fields.Char(string='Number', required=False, readonly=False, copy=False, default='/')

    def _get_sequence(self):
        ''' Return the sequence to be used during the post of the current move.
        :return: An ir.sequence record or False.
        '''
        self.ensure_one()

        journal = self.journal_id
        _logger.info("\n\n\t\t journal =========  %s",journal)
        _logger.info("\n\n\t\t journal.refund_sequence =========  %s",journal.refund_sequence)
        _logger.info("\n\n\t\t journal.sequence_id =========  %s",journal.sequence_id)
        if self.move_type in (
                'entry', 'out_invoice', 'in_invoice', 'out_receipt', 'in_receipt') or not journal.refund_sequence:
            _logger.info("\n\n\t\t return from here =========")
            return journal.sequence_id
        if not journal.refund_sequence_id:
            return
        return journal.refund_sequence_id
    
    # def write(self, vals):
    #     for record in self:
    #         logged_in_user = record.env.user.id
    #         create_user = record.create_uid.id
    #         stage_key = vals.get('approval_stage', '')
    #         if not stage_key and create_user != logged_in_user:
    #             raise UserError(_('Please contact the finance team to make changes to the record.'))

    #     return super(AccountMove, self).write(vals)

    def _post(self, soft=True):
        # OVERRIDE to generate sequence and add as name.
        for move in self:
            _logger.info("\n\n\t\t move.id =========  %s",move.id)
            _logger.info("\n\n\t\t move.company =========  %s",move.company_id)
            if not move.name or move.name == '/':
                # Get the journal's sequence.
                sequence = move._get_sequence()
                _logger.info("\n\n\t\t sequence =========  %s",sequence)
                if not sequence:
                    raise UserError(_('Please define a sequence on your journal.'))

                # Consume a new number.
                move['name'] = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                _logger.info("\n\n\t\t move['name'] =========  %s",move['name'])

        posted = super()._post(soft)
        _logger.info("\n\n\t\t posted =========  %s",posted)
        return posted

    
    def _inter_company_prepare_invoice_data(self, invoice_type):
        _logger.info("\n\n\t\t _inter_company_prepare_invoice_data =============")
        # OVERRIDE to add payment reference.
        self.ensure_one()
        result = super(AccountMove, self)._inter_company_prepare_invoice_data(invoice_type)
        _logger.info("\n\n\t\t result =============%s",result)
        result.update({'payment_reference': self.payment_reference})
        _logger.info("\n\n\t\t result after update =============%s",result)
        return result

    # def _post(self, soft=True):
    #     """Post/Validate the documents.

    #     Posting the documents will give it a number, and check that the document is
    #     complete (some fields might not be required if not posted but are required
    #     otherwise).
    #     If the journal is locked with a hash table, it will be impossible to change
    #     some fields afterwards.

    #     :param soft (bool): if True, future documents are not immediately posted,
    #         but are set to be auto posted automatically at the set accounting date.
    #         Nothing will be performed on those documents before the accounting date.
    #     :return Model<account.move>: the documents that have been posted
    #     """
    #     if soft:
    #         future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
    #         future_moves.auto_post = True
    #         for move in future_moves:
    #             msg = _('This move will be posted at the accounting date: %(date)s',
    #                     date=format_date(self.env, move.date))
    #             move.message_post(body=msg)
    #         to_post = self - future_moves
    #     else:
    #         to_post = self

    #     # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
    #     if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
    #         raise AccessError(_("You don't have the access rights to post an invoice."))
    #     for move in to_post:
    #         if not move.line_ids.filtered(lambda line: not line.display_type):
    #             raise UserError(_('You need to add a line before posting.'))
    #         if move.auto_post and move.date > fields.Date.context_today(self):
    #             date_msg = move.date.strftime(get_lang(self.env).date_format)
    #             raise UserError(_("This move is configured to be auto-posted on %s", date_msg))

    #         if not move.partner_id:
    #             if move.is_sale_document():
    #                 raise UserError(
    #                     _("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
    #             elif move.is_purchase_document():
    #                 raise UserError(
    #                     _("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

    #         if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0,
    #                                                                     precision_rounding=move.currency_id.rounding) < 0:
    #             raise UserError(_(
    #                 "You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))

    #         # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
    #         # lines are recomputed accordingly.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         if not move.invoice_date and move.is_invoice(include_receipts=True):
    #             move.invoice_date = fields.Date.context_today(self)
    #             move.with_context(check_move_validity=False)._onchange_invoice_date()

    #         # When the accounting date is prior to the tax lock date, move it automatically to the next available date.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date) and (
    #                 move.line_ids.tax_ids or move.line_ids.tax_tag_ids):
    #             move.date = move.company_id.tax_lock_date + timedelta(days=1)
    #             move.with_context(check_move_validity=False)._onchange_currency()

    #         if move.name == '/':
    #             # Get the journal's sequence.
    #             sequence = move._get_sequence()
    #             if not sequence:
    #                 raise UserError(_('Please define a sequence on your journal.'))

    #             # Consume a new number.
    #             move['name'] = sequence.with_context(ir_sequence_date=move.date).next_by_id()

    #     # Create the analytic lines in batch is faster as it leads to less cache invalidation.
    #     to_post.mapped('line_ids').create_analytic_lines()
    #     to_post.write({
    #         'state': 'posted',
    #         'posted_before': True,
    #     })

    #     for move in to_post:
    #         move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])

    #         # Compute 'ref' for 'out_invoice'.
    #         if move._auto_compute_invoice_reference():
    #             to_write = {
    #                 'payment_reference': move._get_invoice_computed_reference(),
    #                 'line_ids': []
    #             }
    #             for line in move.line_ids.filtered(
    #                     lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
    #                 to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))
    #             move.write(to_write)

    #     for move in to_post:
    #         if move.is_sale_document() \
    #                 and move.journal_id.sale_activity_type_id \
    #                 and (move.journal_id.sale_activity_user_id or move.invoice_user_id).id not in (
    #         self.env.ref('base.user_root').id, False):
    #             move.activity_schedule(
    #                 date_deadline=min((date for date in move.line_ids.mapped('date_maturity') if date),
    #                                   default=move.date),
    #                 activity_type_id=move.journal_id.sale_activity_type_id.id,
    #                 summary=move.journal_id.sale_activity_note,
    #                 user_id=move.journal_id.sale_activity_user_id.id or move.invoice_user_id.id,
    #             )

    #     customer_count, supplier_count = defaultdict(int), defaultdict(int)
    #     for move in to_post:
    #         if move.is_sale_document():
    #             customer_count[move.partner_id] += 1
    #         elif move.is_purchase_document():
    #             supplier_count[move.partner_id] += 1
    #     for partner, count in customer_count.items():
    #         (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
    #     for partner, count in supplier_count.items():
    #         (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

    #     # Trigger action for paid invoices in amount is zero
    #     to_post.filtered(
    #         lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
    #     ).action_invoice_paid()

    #     # Force balance check since nothing prevents another module to create an incorrect entry.
    #     # This is performed at the very end to avoid flushing fields before the whole processing.
    #     to_post._check_balanced()
    #     return to_post
