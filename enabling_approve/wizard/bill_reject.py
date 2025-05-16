# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class BillReject(models.TransientModel):
    _name = 'bill.reject'
    _description = 'Vendor Bill Reject'

    reason = fields.Text(string='Reason')

    def action_reject_bill(self):
        if self._context.get('active_model') == 'account.move':
            bills = self.env['account.move'].browse(self._context.get('active_ids'))
            filtered_bills = bills.filtered(lambda x:
                           x.approval_stage == 'waiting' and x.first_approver_id.id == self.env.uid or
                           x.approval_stage == 'first_approved' and x.second_approver_id.id == self.env.uid)
            filtered_bills.write({'approval_stage': 'rejected'})
            [bill.message_post(body=self.reason) for bill in filtered_bills]
            for bill in filtered_bills:
                bill.write({'last_reject_reason': self.reason})
                email_values = {'recipient_ids': [(4, bill.create_uid.partner_id.id)]}
                self.env.ref('enabling_approve.email_template_vendor_bill_rejected').send_mail(bill.id, force_send=True, email_values=email_values)
