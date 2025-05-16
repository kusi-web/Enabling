# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)


class AccountAccount(models.Model):
    _inherit = "account.account"

    is_vendor_without_approval = fields.Boolean(string="Vendor bill without approval")


class AccountMove(models.Model):
    _inherit = "account.move"

    is_checkers_requires = fields.Boolean(
        related='company_id.is_checkers_requires',
        readonly=False
    )
    is_second_validation = fields.Boolean(
        related='company_id.is_second_validation',
        readonly=False
    )
    group_by_company = fields.Selection(related='company_id.group_by_company')
    bool_toi_pakihi_rules = fields.Boolean(related='company_id.bool_toi_pakihi_rules',store=True)
    toi_pakihi = fields.Boolean(related='partner_id.toi_pakihi')
    reason_selection = fields.Selection([
        ('1', 'A suitable hapu business could not be found.'),
        ('2', 'A hapu business was not considered as the supply / job was time critical.'),
        ('3', 'The expenditure is $1000 or less (excl. GST).'),
        ('4', 'Other reason (please add details as log note).')
    ], string='Reason', tracking=True)
    reasons_id = fields.Many2one('reasons.toi.pakihi',string="Reasons", tracking=True)
    
    # sushma
    def copy(self, default=None):
        default = dict(default or {})
        _logger.info("\n\n\t\t  ============ default===== %s", default)
        # Clear the reason field when duplicating
        default['reasons_id'] = False
        return super(AccountMove, self).copy(default)

    # sushma
    # po_id = fields.Many2one('purchase.order',string='PO Number',related="invoice_line_ids.purchase_order_id", readonly=False)

    # @api.constrains('ref','company_id')
    # def _check_ref(self):
    #     for item in self:
    #         if item.company_id.group_by_company == 'wm' and not item.ref:
    #             raise ValidationError("Enter Bill / Vendor Refernce")
    #     return True
    # EOL==

    def _domain_first_approver(self):
        company = self.env.company
        if company.is_checkers_requires and company.is_second_validation:
            ids = company.first_approver_ids.ids
            return [('id', 'in', ids)]
        else:
            analytic_account_id = self.analytic_account_id
            approval_id = self.analytic_account_id.approval_id
            amount = self.amount_total
            if analytic_account_id or approval_id or approval_id.approval_user_ids:
                    ids = approval_id.sudo().approval_user_ids.filtered(
                        lambda a: a.from_amount <= amount and a.to_amount >= amount).mapped('user_ids')
                    return [('id', 'in', ids)]
            else:
                return [('id', 'in', [])]

    def _domain_second_approver(self):
        company = self.env.company
        if company.is_checkers_requires and company.is_second_validation:
            ids = company.second_approver_ids.ids
            return [('id', 'in', ids)]
        else:
            analytic_account_id = self.analytic_account_id
            approval_id = self.analytic_account_id.approval_id
            amount = self.amount_total
            if analytic_account_id or approval_id or approval_id.approval_user_ids:
                    ids = approval_id.sudo().approval_user_ids.filtered(
                        lambda a: a.from_amount <= amount and a.to_amount >= amount and a.required_second_approval == 'yes').mapped('second_approver_user_ids')
                    return [('id', 'in', ids)]
            else:
                return [('id', 'in', [])]

    @api.onchange('analytic_account_id')
    def _onchange_domain_first_approver(self):
        domain = {}
        company = self.env.company
        if company.is_checkers_requires and company.is_second_validation:
            ids = company.first_approver_ids.ids
            domain.update({'first_approver_id': [('id', 'in', ids)]})
            return {'domain': domain}
        else:
            analytic_account_id = self.analytic_account_id
            approval_id = self.analytic_account_id.approval_id
            amount = self.amount_total
            if analytic_account_id or approval_id or approval_id.approval_user_ids:
                ids = approval_id.sudo().approval_user_ids.filtered(lambda a: a.from_amount <= amount and a.to_amount >= amount).mapped('user_ids')
                domain.update({'first_approver_id': [('id', 'in', ids.ids)]})
            else:
                domain.update({'first_approver_id': [('id', 'in', [])]})
        return {'domain': domain}

    @api.onchange('analytic_account_id')
    def _onchange_domain_second_approver(self):
        domain = {}
        company = self.env.company
        if company.is_checkers_requires and company.is_second_validation:
            ids = company.second_approver_ids.ids
            domain.update({'second_approver_id': [('id', 'in', ids)]})
        else:
            analytic_account_id = self.analytic_account_id
            approval_id = self.analytic_account_id.approval_id
            amount = self.amount_total
            if analytic_account_id or approval_id or approval_id.approval_user_ids:
                ids = approval_id.sudo().approval_user_ids.filtered(
                    lambda a: a.from_amount <= amount and a.to_amount >= amount and a.required_second_approval == 'yes').mapped('second_approver_user_ids')
                domain.update({'second_approver_id': [('id', 'in', ids.ids)]})
            else:
                domain.update({'second_approver_id': [('id', '=', [])]})
        return {'domain':domain}

    @api.model
    def _get_default_customer_payment(self):
        categ_id = self.env['res.partner.category'].search([('name','=','DD')])
        if categ_id:
            return categ_id

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    tolerance_percentage = fields.Char(
        related='company_id.tolerance_percentage',
        readonly=False
    )
    tolerance_price = fields.Monetary(
        related='company_id.tolerance_price',
        readonly=False
    )

    first_approver_id = fields.Many2one('res.users', domain=_domain_first_approver, string='First Approver')
    second_approver_id = fields.Many2one('res.users', domain=_domain_second_approver, string='Second Approver')
    approval_stage = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('waiting', 'Waiting for First Approval'),
        ('first_approved', 'Waiting for Second Approval'),
        ('final_approved', 'Final Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Stage', copy=False, tracking=True, default='not_sent')
    show_first_approval = fields.Boolean(compute='_compute_show_approval')
    show_second_approval = fields.Boolean(compute='_compute_show_approval')
    show_recall_btn = fields.Boolean(compute='_compute_recall')
    po_number = fields.Char(string='PO Number')
    last_reject_reason = fields.Text(string='Last Reject Reason')
    x_css = fields.Html(
        string='CSS',
        sanitize=False,
        compute='_compute_css',
        store=False,
    )
    category_id = fields.Many2one('res.partner.category',string='Customer Payment',default=_get_default_customer_payment)

    @api.depends('approval_stage', 'first_approver_id', 'second_approver_id')
    def _compute_recall(self):
        for record in self:
            if record.first_approver_id and record.approval_stage == 'waiting':
                record.show_recall_btn = True
            elif record.second_approver_id and record.approval_stage == 'first_approved':
                record.show_recall_btn = True
            else:
                record.show_recall_btn = False

    @api.depends('approval_stage')
    def _compute_css(self):
        for application in self:
            if application.approval_stage in ('first_approved', 'final_approved'):
                application.x_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                application.x_css = False

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        action_first_approve = False
        action_final_approve_validate = False
        action_reject_bill = False
        if toolbar:
            for action in res['toolbar'].get('action'):
                if action.get('xml_id'):
                    if self._context.get('default_move_type') == 'out_invoice' or self._context.get('default_move_type') == 'out_refund' or self._context.get('default_move_type') == 'out_receipt':
                        if action['xml_id'] == 'enabling_approve.first_approve_vendor_bill_server_action_batch':
                            action_first_approve = action

                        if action['xml_id'] == 'enabling_approve.action_final_approve_validate_account_move':
                            action_final_approve_validate = action

                        if action['xml_id'] == 'enabling_approve.account_reject_bill_multi':
                            action_reject_bill = action

                    if self._context.get('default_move_type') == 'in_invoice' or self._context.get('default_move_type') == 'in_refund' or self._context.get('default_move_type') == 'in_receipt':
                        if action['xml_id'] == 'account.action_validate_account_move':
                            res['toolbar']['action'].remove(action)

            if action_first_approve: res['toolbar']['action'].remove(action_first_approve)
            if action_final_approve_validate: res['toolbar']['action'].remove(action_final_approve_validate)
            if action_reject_bill: res['toolbar']['action'].remove(action_reject_bill)
        return res

    @api.depends('approval_stage', 'first_approver_id', 'second_approver_id')
    def _compute_show_approval(self):
        for record in self:
            if record.first_approver_id.id == self.env.uid and record.approval_stage == 'waiting':
                record.show_first_approval = True
            else:
                record.show_first_approval = False

            if record.second_approver_id.id == self.env.uid and record.approval_stage == 'first_approved':
                record.show_second_approval = True
            else:
                record.show_second_approval = False

    def send_mail_to_approver(self, approver_id):
        view_context = dict(self._context)
        url = self.env['ir.config_parameter'].get_param('web.base.url')
        url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        view_context.update({'link': url})
        approver = self.env['res.users'].browse(approver_id)
        email_values = {'recipient_ids': [(4, approver.partner_id.id)]}
        #self.env.ref('enabling_approve.email_template_vendor_bill_approval').with_context(view_context).send_mail(
        #    self.id, force_send=True,
        #    email_values=email_values)

    def action_recall(self):
        self.write({'approval_stage': 'not_sent'})

    def action_request_approval(self):
        # sushma== Check if the amount and vendor are the same
        for move in self:
            _logger.info("\n\n\t\t move.move_type =================%s",move.move_type)
            _logger.info("\n\n\t\tmove.company_id.group_by_company =================%s",move.company_id.group_by_company)
            
            if move.move_type == 'in_invoice' and move.company_id.group_by_company == 'wr':
                # Get the date 12 months ago
                twelve_months_ago = move.invoice_date - timedelta(days=365)
                _logger.info("\n\n\t\t twelve_months_ago =================%s",twelve_months_ago)
                # Get all companies in the same group (WR)
                wr_companies = self.env['res.company'].search([('group_by_company', '=', 'wr')])
                _logger.info("\n\n\t\t WR Companies =================%s", wr_companies)

                # Show popup message
                duplicate_bills = self.env['account.move'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('amount_total', '=', move.amount_total),
                    ('invoice_date', '>=', twelve_months_ago),
                    ('id', '!=', move.id),  # Exclude the current bill
                    ('move_type', '=', 'in_invoice'),
                    ('state', '!=', 'cancel'),  # Exclude cancelled bills
                    ('company_id', 'in', wr_companies.ids),  # Include all companies in the same group

                ])
                _logger.info("\n\n\t\t duplicate_bills =================%s",duplicate_bills)

                if duplicate_bills:
                    return {
                        'name': 'Warning',
                        'type': 'ir.actions.act_window',
                        'res_model': 'duplicate.vendor.bill.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_move_id': self.id,
                            'default_warning_message': 'Vendor with the same amount detected in the last 12 months',
                        }
                    }
                else:
                    return move._continue_approval_logic()
            else:
                return move._continue_approval_logic()
        # EOL

    def _continue_approval_logic(self):
        """This function contains the rest of the logic to be called after the wizard confirmation."""

        purchase_id = self.env['purchase.order'].search([('name', '=', self.invoice_origin)], limit=1)
        if self.group_by_company == 'wm' and not self.partner_bank_id.state == 'authorised':
            raise UserError(_('The Bank Account is not Authorised.'))
        if purchase_id and not any((not line.account_id.is_vendor_without_approval) for line in self.invoice_line_ids if not line.purchase_line_id):
            amt_diff = self.amount_total - purchase_id.amount_total
            amt_per = (purchase_id.amount_total * round(float(self.tolerance_percentage))) / 100
            if purchase_id.amount_total == self.amount_total:
                self.action_post()
            else:
                if amt_diff < self.tolerance_price or amt_diff < amt_per:
                    self.action_post()
                else:
                    if not self.ref:
                        raise UserError(_('The Bill Reference should be filled in.'))
                    if not self.partner_bank_id.id:
                        raise UserError(_('The Bank Account should be filled in.'))
                    first_approver = self.first_approver_id
                    if not first_approver:
                        raise UserError(_('The First Approver has to be assigned before you can request for approval.'))
                    # second_approver = self.second_approver_id
                    # if not second_approver:
                    #     raise UserError(_('The Second Approver has to be assigned before you can request for approval.'))

                    if first_approver:
                        self.send_mail_to_approver(first_approver.id)

                    self.write({'approval_stage': 'waiting'})
        else:
            if not self.ref:
                raise UserError(_('The Bill Reference should be filled in.'))
            if not self.partner_bank_id.id:
                raise UserError(_('The Bank Account should be filled in.'))
            first_approver = self.first_approver_id
            if not first_approver:
                raise UserError(_('The First Approver has to be assigned before you can request for approval.'))
            # second_approver = self.second_approver_id
            # if not second_approver:
            #     raise UserError(_('The Second Approver has to be assigned before you can request for approval.'))
            if first_approver:
                self.send_mail_to_approver(first_approver.id)
            self.write({'approval_stage': 'waiting'})


    def action_first_approve_multi(self):
        self.filtered(
            lambda x: x.approval_stage == 'waiting' and x.first_approver_id.id == self.env.uid
        ).write({'approval_stage': 'first_approved'})

    def action_final_approve_multi(self):
        res = super(AccountMove, self).validate_move()
        self.filtered(
            lambda x: x.approval_stage == 'first_approved' and x.second_approver_id.id == self.env.uid
        ).write({'approval_stage': 'final_approved'})
        return res

    def action_approve_new(self):
        second_approver = self.second_approver_id
        if not self.is_second_validation:
            self.action_post()
            return True
        if not second_approver:
            raise UserError(_('The Second Approver has to be assigned before you can do the first level approval.'))
        else:
            self.send_mail_to_approver(second_approver.id)
            self.write({'approval_stage': 'first_approved'})
            return True

    def action_approve(self):
        if self.bool_toi_pakihi_rules and not self.toi_pakihi:
            view_id = self.env.ref('enabling_approve.approval_wizard_form_view').id
            return {
                'name': 'The Vendor is not a Toi Pakihi. Please select a reason why a Toi Pakihi has not been chosen',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'approval.wizard',
                'view_id': view_id,
                'target': 'new',
                'context': {'default_move_id': self.id}
            }
        else:
            self.action_approve_new()
        # second_approver = self.second_approver_id
        # if not self.is_second_validation:
        #     self.action_post()
        #     return True
        # if not second_approver:
        #     raise UserError(_('The Second Approver has to be assigned before you can do the first level approval.'))
        # else:
        #     self.send_mail_to_approver(second_approver.id)
        #     self.write({'approval_stage': 'first_approved'})
        #     return True

    def action_post(self):
        if not self.partner_bank_id.id and self.category_id.name == "DD" and self.journal_id.name == "Customer Invoices" and (self.company_id.name == "ER - Eastcliffe Orakei Retirement Care" or self.company_id.name == "EM - Eastcliffe Orakei Management Services" ):
            raise ValidationError(_('The Bank Account should be filled in for payment type DD'))
        res = super(AccountMove, self).action_post()
        self.write({'approval_stage': 'final_approved'})
        return res

    def action_reject(self):
        ''' Open the bill.reject wizard to reject the selected vendor bills.
        :return: An action opening the bill.reject wizard.
        '''
        return {
            'name': _('Reject Bill'),
            'res_model': 'bill.reject',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


#sushma
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('move_id')
    def _compute_analytic_account(self):
        super()._compute_analytic_account()
        _logger.info("\n\n\t\t _compute_analytic_account =====================")
        for line in self:
            _logger.info("\n\n\t\t line.move_id.company_id.group_by_company =====================%s",line.move_id.company_id.group_by_company)

            if line.move_id.company_id.group_by_company == 'wm':
                if line.purchase_order_id:
                    line.analytic_account_id=line.purchase_order_id.analytic_account_id
                    line.move_id.project_id=line.purchase_order_id.project_id or line.project_id
                    line.move_id.task_id=line.purchase_order_id.task_id or line.task_id
                    line.move_id.task_line_id=line.purchase_order_id.task_line_id or line.task_line_id
                    line.move_id.po_number=line.purchase_order_id.name
                    _logger.info("\n\n\t\t move_id.project_id =====================%s",line.move_id.project_id)
# #EOL