# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    name = fields.Char(compute="_compute_name_by_sequence")

    
    # def _compute_name_by_sequence(self):
    #     self.filtered(lambda l: l.journal_id.type == 'purchase')._compute_name()

    #     # print('\n\n=============vvvvvvvvv',self._compute_name())
    #     # if self.env.company.name == 'HITECH FORMULATIONS PRIVATE LIMITED-BADDI' and (self.partner_id.name == 'LYRA LABORATORIES PRIVATE LIMITED-BADDI (MDC)' or self.partner_id.name == 'LYRA LABORATORIES PRIVATE LIMITED-BADDI'):
    #     if self.env.company.name == 'HITECH FORMULATIONS PRIVATE LIMITED-BADDI' and (self.partner_id.name == 'LYRA LABORATORIES PRIVATE LIMITED-BADDI (MDC)'):
    #         for move in self.filtered(lambda l: l.journal_id.type != 'purchase'):
    #             name = move.name or "/"
    #             if (
    #                     move.state == "posted"
    #                     and (not move.name or move.name == "/")
    #                     and move.journal_id
    #                     and move.journal_id.lyra_company_sequence
    #             ):
    #                 if (
    #                         move.move_type in ("out_refund", "in_refund")
    #                         and move.journal_id.type in ("sale", "purchase")
    #                         and move.journal_id.refund_sequence
    #                         and move.journal_id.lyra_company_refund_sequence
    #                 ):
    #                     seq = move.journal_id.lyra_company_refund_sequence
    #                 else:
    #                     seq = move.journal_id.lyra_company_sequence
    #                 name = seq.next_by_id(sequence_date=move.date)
    #             move.name = name
    #             move.payment_reference = name if move.move_type == "out_invoice" and move.state == 'posted' else False
    #     else:
    #         for move in self.filtered(lambda l: l.journal_id.type != 'purchase'):
    #             name = move.name or "/"
    #             if (
    #                     move.state == "posted"
    #                     and (not move.name or move.name == "/")
    #                     and move.journal_id
    #                     and move.journal_id.sequence_id
    #             ):
    #                 if (
    #                         move.move_type in ("out_refund", "in_refund")
    #                         and move.journal_id.type in ("sale", "purchase")
    #                         and move.journal_id.refund_sequence
    #                         and move.journal_id.refund_sequence_id
    #                 ):
    #                     seq = move.journal_id.refund_sequence_id
    #                 else:
    #                     seq = move.journal_id.sequence_id
    #                 name = seq.next_by_id(sequence_date=move.date)
    #             move.name = name
    #             move.payment_reference = name if move.move_type == "out_invoice" and move.state == 'posted' else False

    @api.depends("state", "journal_id", "date")
    def _compute_name_by_sequence(self):

        for move in self:
            name = move.name or "/"
            if (
                    move.state == "posted"
                    and (not move.name or move.name == "/")
                    and move.journal_id
                    and move.journal_id.sequence_id
            ):
                if (
                        move.move_type in ("out_refund", "in_refund")
                        and move.journal_id.type in ("sale", "purchase")
                        and move.journal_id.refund_sequence
                        and move.journal_id.refund_sequence_id
                ):
                    seq = move.journal_id.refund_sequence_id
                else:
                    seq = move.journal_id.sequence_id
                name = seq.next_by_id(sequence_date=move.date)

            # if move.state == 'posted' and move.journal_id.type == 'purchase':   
            #     seg_name = name.split('/')
            #     month =  move.date.month
            #     year =  move.date.year
            #     month = '0' + str(month) if len(str(month)) == 1 else str(month)
            #     seg_name[1] = str(year) + '/' + str(month)
            #     name = '/'.join(seg_name)
                

            move.name = name

            move.payment_reference = name if move.move_type == "out_invoice" and move.state == 'posted' else False

    def _constrains_date_sequence(self):
        return True

