# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_invoice_date(self):
        return fields.Date.context_today(self) if self._context.get('default_move_type',
                                                                    'entry') in self.get_purchase_types(
            include_receipts=True) else False

    # New Fields
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string="Task", domain="[('project_id', '=', project_id)]")
    task_line_id = fields.Many2one('project.task.item', string='Task Line Item', domain="[('task_id', '=', task_id)]")
    recurring_doc = fields.Boolean(string='RC',readonly=True)

    # Overidden Fileds
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, tracking=True, index=True, copy=False,
                            #    states={'draft': [('readonly', False)]},
                               default=_get_default_invoice_date)
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        readonly=True,
        tracking=True,
        # states={'draft': [('readonly', False)]},
        copy=False,
        default=fields.Date.context_today
    )
    partner_bank_id = fields.Many2one('res.partner.bank', string='Recipient Bank', tracking=True,
                                      help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.',
                                      check_company=True)

#    _sql_constraints = [
#        ('vendor_reference_uniq', 'unique (partner_id,ref)', 'The Bill Reference must be unique per vendor !')
#    ]

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.task_id = False
        self.task_line_id = False

    @api.onchange('task_id')
    def _onchange_task_id(self):
        self.task_line_id = False

class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "mail.thread"]

    project_id = fields.Many2one('project.project', tracking=True, string='Project')
    task_id = fields.Many2one('project.task', tracking=True, domain="[('project_id', '=', project_id)]", string="Task")
    task_line_id = fields.Many2one('project.task.item', tracking=True, domain="[('task_id', '=', task_id)]", string='Task Line Item')
    parent_invoice_partner_display_name = fields.Char(related='move_id.invoice_partner_display_name', store=True)
    invoice_date = fields.Date(related='move_id.invoice_date', store=True)
    payment_state = fields.Selection(related='move_id.payment_state', store=True, readonly=True)
    invoice_date_due = fields.Date(related='move_id.invoice_date_due', string='Due Date ')
    taskline_account_id = fields.Many2one(related='task_line_id.account_id', string="Account ", store=True, readonly=True)
    taskline_analytic_account_id = fields.Many2one(related='task_line_id.analytic_account_id', string="Analytic Account ", store=True, readonly=True)

    # Overidden Fileds
    analytic_account_id = fields.Many2one('account.analytic.account', tracking=True, string='Analytic Account',
                                          index=True, compute="_compute_analytic_account", store=True, readonly=False,
                                          check_company=True, copy=True)
    quantity = fields.Float(string='Quantity', tracking=True,
                            default=1.0, digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.")
    price_unit = fields.Float(string='Unit Price', tracking=True, digits='Product Price')
    recurring_invoice = fields.Boolean(default=False)
    # is_checkers_requires = fields.Boolean(
    #     related='company_id.is_checkers_requires',
    #     readonly=False
    # )
    # is_second_validation = fields.Boolean(
    #     related='company_id.is_second_validation',
    #     readonly=False
    # )


    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id and self.project_id != self.task_id.project_id:
            self.task_id = False
            self.task_line_id = False

    @api.onchange('task_id')
    def _onchange_task_id(self):
        if self.task_id:
            self.task_line_id = False

    @api.onchange('task_line_id')
    def _onchange_task_line_id(self):
        if self.task_line_id:
            self.account_id = self.task_line_id.account_id and self.task_line_id.account_id.id or False
            self.analytic_account_id = self.task_line_id.analytic_account_id and self.task_line_id.analytic_account_id.id or False

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account_id(self):
        if self.move_id.is_purchase_document():
            if self.move_id.partner_id and self.move_id.partner_id.property_account_position_id.id is False:
                if self.analytic_account_id and self.analytic_account_id.purchase_tax_id.id is not False:
                    self.tax_ids = [(6, 0, [self.analytic_account_id.purchase_tax_id.id])]
                else:
                    self.tax_ids = self._get_computed_taxes()

        if self.move_id.is_sale_document():
            if self.move_id.partner_id and self.move_id.partner_id.property_account_position_id.id is False:
                if self.analytic_account_id and self.analytic_account_id.sale_tax_id.id is not False:
                    self.tax_ids = [(6, 0, [self.analytic_account_id.sale_tax_id.id])]
                else:
                    self.tax_ids = self._get_computed_taxes()

    @api.constrains('account_id','analytic_account_id','analytic_tag_ids')
    def _check_account_id(self):
        for line in self:
            # if not line.recurring_invoice: #This line helps to by pass the below warning messages when creating invoice from recurring invoice
            if line.account_id.requires_project_code is True and line.project_id.id is False:
                raise UserError(_('Lines with accounts "Requires Project Code = TRUE" cannot be saved without Projects.'))

            if line.account_id.requires_analytic_account is True and line.analytic_account_id.id is False:
                raise UserError(_('Lines with accounts "Requires Analytic Account = TRUE" cannot be saved without Analytic Accounts.'))

            if line.account_id.requires_analytic_tags is True and len(line.analytic_tag_ids.ids) == 0:
                raise UserError(_('Lines with accounts "Requires Analytic Tags = TRUE" cannot be saved without Analytic Tags.'))

    def write(self, vals):
        _logger.info("\n\n\t\tWRITE ===========move line======= vals ===== %s", vals)
        old_val = ''
        new_val = ''
        if self.tax_ids:
            old_val = self.tax_ids.mapped('name')
        res = super(AccountMoveLine, self).write(vals)

        if self.tax_ids:
            new_val = self.tax_ids.mapped('name')
        if old_val != new_val:
            trackings = []
            message_id = self.move_id.message_post(body=f'<strong>{ self._description }:</strong> { self.display_name }<br/><ul> Taxes: { old_val } --> { new_val }<ul/>').id
            _logger.info("\n\n\t\t message_id ======111======= %s",message_id)
            if self.message_ids:
                trackings = self.env['mail.tracking.value'].sudo().search([('mail_message_id', '=', self.message_ids[0].id)])
            _logger.info("\n\n\t\t trackings ======111======= %s",trackings)
            for tracking in trackings:
                tracking.copy({'mail_message_id': message_id})
        if 'tax_ids' in vals:
            _logger.info("\n\n\t\tupdatign taxes ====111=========")
        return res
    
    @api.depends('move_id')
    def _compute_analytic_account(self):
        # Try calling super method if it exists
        super_method = getattr(super(AccountMoveLine, self), '_compute_analytic_account', None)
        if callable(super_method):
            super_method()

        _logger.info("Starting _compute_analytic_account")
        for line in self:
            company = line.move_id.company_id
            if not company:
                _logger.warning("No company set for move %s", line.move_id.id)
                continue

            group = getattr(company, 'group_by_company', False)
            _logger.info("Company group_by_company: %s", group)

            if group == 'wm':
                if line.purchase_order_id:
                    line.analytic_account_id = line.purchase_order_id.analytic_account_id
                    line.move_id.project_id = line.purchase_order_id.project_id or line.project_id
                    line.move_id.task_id = line.purchase_order_id.task_id or line.task_id
                    line.move_id.task_line_id = line.purchase_order_id.task_line_id or line.task_line_id
                    line.move_id.po_number = line.purchase_order_id.name
                    _logger.info("Set project and task from purchase order %s", line.purchase_order_id.name)

