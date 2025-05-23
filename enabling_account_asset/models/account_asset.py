# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import Store
import calendar
from pickle import FALSE
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError
from math import copysign
from datetime import date, datetime,timedelta
import pytz; pytz.timezone("Pacific/Auckland")
import logging
_logger = logging.getLogger(__name__)

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    @api.model
    def _valid_field_parameter(self, field, name):
        return name in ['states', 'tracking'] or super()._valid_field_parameter(field, name)

    # Newly added fields
    asset_type = fields.Selection([
        ('purchase', 'Purchase'),
        ('expense', 'Expense'),
        ('sale', 'Sale'),
    ], default='purchase', string='Asset Type', required=True)
    asset_model = fields.Many2one('account.asset', domain="[('state', '=', 'model')]", string='Asset Model')
    take_on_asset = fields.Boolean('Take On Asset')
    takeon_accumulated_depreciation = fields.Float('Takeon Accumulated Depreciation')
    takeon_accumulated_depreciation_tax = fields.Float('Takeon Accumulated Tax Depr')
    depreciation_percentage = fields.Float(string='Depreciation %')

    # Newly added fields for Tax Values
    original_value = fields.Monetary(string="Value", compute='_compute_value', store=True, readonly=True, states={'draft': [('readonly', False)]})
    total_cost = fields.Monetary(string="Total Cost", compute='_compute_total_cost_value', store=True, readonly=True)
    tax_original_value = fields.Monetary(string="Value", compute='_compute_value_tax', store=True, readonly=True)
    book_value = fields.Monetary(string='Net Book Value', readonly=True, compute='_compute_book_value', store=True, help="Sum of the depreciable value, the salvage value and the book value of all value increase items")
    tax_book_value = fields.Monetary(string='Net Tax Value', readonly=True, compute='_compute_tax_book_value', store=False, recursive=True)

    value_residual = fields.Monetary(string='Prior Accumulated Depreciation', readonly=True, compute='_compute_value_residual', store=True)
    value_residual_sale = fields.Monetary(string='Accumulated Depreciation', readonly=True, store=True,default=0)
    proceeds_from_sale = fields.Monetary(string='Proceeds from Sale/Disposal', readonly=True, compute='_compute_proceeds_from_sale', store=True)

    tax_value_residual = fields.Monetary(string='Accumulated Depreciation', readonly=True, compute='_compute_value_residual', store=True)
    tax_accumulated_dep = fields.Monetary(string='Accumulated Depreciation as of today', readonly=True, compute='_compute_tax_accumulated_dep', store=False)
    salvage_value = fields.Monetary(string='Not Depreciable Value', readonly=True, states={'draft': [('readonly', False)]},
                                    help="It is the amount you plan to have that you cannot depreciate.")
    tax_salvage_value = fields.Monetary(string='Not Depreciable Value', readonly=True,
                                    states={'draft': [('readonly', False)]},
                                    help="It is the tax amount you plan to have that you cannot depreciate.")
    tax_acquisition_date = fields.Date(states={'draft': [('readonly', False)]}, default=fields.Date.context_today)
    
    acquisition_date =fields.Date(states={'draft': [('readonly', False)]}, compute='_compute_acquisition_date',store = True)
    first_depreciation_date =fields.Date(states={'draft': [('readonly', False)]}, compute='_compute_first_depreciation_date',store = True)

    # new_acquisition_date = fields.Date(states={'draft': [('readonly', False)]}, default=fields.Date.context_today)
    new_acquisition_date = fields.Date(states={'draft': [('readonly', False)]}, default='')

    # new_first_depreciation_date = fields.Date(states={'draft': [('readonly', False)]}, default=fields.Date.context_today)
    new_first_depreciation_date = fields.Date(states={'draft': [('readonly', False)]}, default='')

    # Newly added field to Link with Tax Depreciation lines
    tax_depreciation_move_ids = fields.One2many('account.asset.tax', 'asset_id', string='Tax Depreciation Lines', readonly=True,
                                            states={'draft': [('readonly', False)], 'open': [('readonly', False)],
                                                    'paused': [('readonly', False)]})

    # Newly added fields for Tax Depreciation params
    tax_method = fields.Selection([('linear', 'Straight Line'), ('degressive', 'Declining'),
                               ('degressive_then_linear', 'Declining then Straight Line')], string='Method',
                              readonly=True, states={'draft': [('readonly', False)], 'model': [('readonly', False)]},
                              default='linear',
                              help="Choose the method to use to compute the amount of depreciation lines.\n"
                                   "  * Straight Line: Calculated on basis of: Gross Value / Number of Depreciations\n"
                                   "  * Declining: Calculated on basis of: Residual Value * Declining Factor\n"
                                   "  * Declining then Straight Line: Like Declining but with a minimum depreciation value equal to the straight line value.")
    tax_method_number = fields.Integer(string='Number of Depreciations', readonly=True,
                                   states={'draft': [('readonly', False)], 'model': [('readonly', False)]}, default='',
                                   help="The number of depreciations needed to depreciate your asset")
    tax_method_period = fields.Selection([('1', 'Months'), ('12', 'Years')], string='Number of Months in a Period',
                                     readonly=True, default='1',
                                     states={'draft': [('readonly', False)], 'model': [('readonly', False)]},
                                     help="The amount of time between two depreciations")
    tax_method_progress_factor = fields.Float(string='Declining Factor', readonly=True, default=0.3,
                                          states={'draft': [('readonly', False)], 'model': [('readonly', False)]})
    tax_depreciation_percentage = fields.Float(string='Depreciation %')
    tax_prorata = fields.Boolean(string='Prorata Temporis', readonly=True,
                             states={'draft': [('readonly', False)], 'model': [('readonly', False)]},
                             help='Indicates that the first depreciation entry for this asset have to be done from the asset date (purchase date) instead of the first January / Start date of fiscal year')
    tax_prorata_date = fields.Date(
        string='Prorata Date',
        readonly=True, states={'draft': [('readonly', False)]})
    # tax_first_depreciation_date = fields.Date(
    #     string='First Depreciation Date',
    #     compute='_compute_tax_first_depreciation_date', store=True, readonly=False,
    #     help='Note that this date does not alter the computation of the first journal entry in case of prorata temporis assets. It simply changes its accounting date')
    tax_first_depreciation_date = fields.Date(
        string='First Depreciation Date', store=True, readonly=False,
        help='Note that this date does not alter the computation of the first journal entry in case of prorata temporis assets. It simply changes its accounting date')

    # Newly added hidden fields
    tax_depreciation_entries_count = fields.Integer(compute='_tax_entry_count', string='# Tax Depreciation Entries',
                                                      help="Number of tax depreciation entries")

    # Overridden
    method_period = fields.Selection([('1', 'Months'), ('12', 'Years')], string='Number of Months in a Period',
                                     readonly=True, default='1',
                                     states={'draft': [('readonly', False)], 'model': [('readonly', False)]},
                                     help="The amount of time between two depreciations")

    #Newly added field
    employee_id = fields.Many2one("enabling.employee", string='Employee')

    # fields defined in odoo front end
    x_purch_price = fields.Monetary(string="Purchase Price")
    tax_purch_price = fields.Monetary(string="Tax Purchase Price", store=True)
    x_book_reval = fields.Monetary(string="Revaluation",compute="_compute_value_revaluation", store=True)
    x_value_addition = fields.Monetary(string="Addition", compute="_compute_x_value_addition", store=True)
    tax_x_value_addition = fields.Monetary(string="Tax Addition", compute="_compute_x_value_addition", store=True, readonly= True)
    value_addition = fields.Boolean(string="Value edition done", compute="_compute_x_value_addition", store=True)
    x_monthly_depr = fields.Monetary(string="Monthly Depreciation", compute="_compute_x_monthly_depr", store=True)
    tax_monthly_depr = fields.Monetary(string="Tax Monthly Depreciation", compute="_compute_tax_monthly_depr",store=True, readonly= True)
    # tax_monthly_depr = fields.Monetary(string="Tax Monthly Depreciation",store=True, readonly= True)
    value_revaluation = fields.Boolean(string="Value edition done", compute="_compute_value_revaluation", store=True)

    # add value
    add_value_count = fields.Integer(compute='_entry_add_value_list', string='# Value Addition list')
    revalue_count = fields.Integer(compute='_entry_revalue_list', string='# Revalue list')

    seq_no = fields.Char('Order Reference', required=True, index=True, copy=False, default='New')
    group_id = fields.Many2one('account.asset.group', string="Asset Group")
    asset_revalue_ids = fields.One2many('asset.revalue', 'asset_id', string="Asset Revalues")
    asset_value_addition_ids = fields.One2many('asset.value.addition', 'asset_id', string="Asset Value Additions")

    # display_model_choice = fields.Boolean(compute="_compute_display_model_choice")
    display_account_asset_id = fields.Boolean(compute="_compute_display_account_asset_id")
    total_depreciation = fields.Monetary(string="Total Depreciation", compute="_compute_total_depreciation", store=True)
    
    @api.depends('acquisition_date')
    def _compute_acquisition_date(self):
        for record in self:
            if record.acquisition_date == '':
                record.acquisition_date = self.new_acquisition_date

    @api.depends('first_depreciation_date')
    def _compute_first_depreciation_date(self):
        for record in self:
            if record.first_depreciation_date == '':
                record.first_depreciation_date = self.new_first_depreciation_date

    @api.depends('depreciation_move_ids', 'depreciation_move_ids.date', 'depreciation_move_ids.state', 'depreciation_move_ids.amount_total')
    def _compute_x_monthly_depr(self):
        for record in self:
            record.x_monthly_depr = 0.00
            depreciation_move_ids = record.depreciation_move_ids.filtered(lambda r: r.state not in ['posted', 'cancel'])
            if depreciation_move_ids:
                depreciation_move_ids = depreciation_move_ids.sorted(key=lambda r: r.date)
                record.x_monthly_depr = depreciation_move_ids[0].amount_total

    @api.depends('tax_depreciation_move_ids','tax_depreciation_move_ids.date', 'tax_depreciation_move_ids.depreciation')
    def _compute_tax_monthly_depr(self):
        for record in self:
            record.tax_monthly_depr = 0.00
            # tax_depreciation_move_ids = record.tax_depreciation_move_ids
            if record.tax_depreciation_move_ids:
                tax_depreciation_move_ids = record.tax_depreciation_move_ids.sorted(key=lambda r: r.date)
                record.tax_monthly_depr = tax_depreciation_move_ids[0].depreciation

    @api.depends('already_depreciated_amount_import', 'depreciation_move_ids', 'depreciation_move_ids.state')
    def _compute_total_depreciation(self):
        for record in self:
            record.total_depreciation = (record.already_depreciated_amount_import
                + sum(
                    record.depreciation_move_ids
                        .filtered(lambda m: m.state == 'posted' and not m.reversal_move_id and not m.ref.endswith(': Sale') and not m.ref.endswith(': Disposal'))
                        .line_ids
                        #   .filtered(lambda l: l.account_id == record.account_depreciation_id)
                        # .filtered(lambda l:l.account_id != FALSE)
                        .filtered(lambda l:l.account_id)
                        .mapped('credit' if record.asset_type in ('expense', 'purchase') else 'debit')
                )
            )

    @api.depends('original_value', 'tax_original_value', 'salvage_value', 'tax_salvage_value', 'takeon_accumulated_depreciation', 'takeon_accumulated_depreciation_tax', 'already_depreciated_amount_import', 'depreciation_move_ids.state', 'children_ids.book_value', 'state', 'asset_revalue_ids')
    def _compute_value_residual(self):
        for record in self:
            # if record.asset_revalue_ids:
            #     record.value_residual =  0.0
            #     record.tax_value_residual = 0.0
            # else:
            record.value_residual = (
                record.already_depreciated_amount_import
                + sum(
                    record.depreciation_move_ids
                            .filtered(lambda m: m.state == 'posted' and not m.reversal_move_id)
                            .line_ids
                        #   .filtered(lambda l: l.account_id == record.account_depreciation_id)
                            .filtered(lambda l:l.account_id)
                            .mapped('credit' if record.asset_type in ('expense', 'purchase') else 'debit')
                )
            )
            record.tax_value_residual = record.tax_original_value - record.tax_salvage_value
            if record.state == 'close':
                record.value_residual = record.value_residual
                record.tax_value_residual =  record.tax_value_residual

            # if record.state == 'close':
            #     record.value_residual = record.value_residual + record.original_value - record.salvage_value - record.takeon_accumulated_depreciation + sum(record.children_ids.mapped('book_value'))
            #     record.tax_value_residual =  record.tax_value_residual + record.tax_original_value - record.tax_salvage_value - record.takeon_accumulated_depreciation_tax - record.tax_value_residual + sum(record.children_ids.mapped('tax_book_value'))

    # @api.depends('proceeds_from_sale','original_value','value_residual')
    @api.depends('total_cost','value_residual')
    def _compute_proceeds_from_sale(self):
        _logger.info("\n\n\t\t _compute_proceeds_from_sale ===============")
        for record in self:
            record.proceeds_from_sale = record.total_cost - record.value_residual
    
    @api.depends('tax_accumulated_dep','tax_depreciation_move_ids.date','state')
    def _compute_tax_accumulated_dep(self):
        for record in self:
            todaysdate = fields.Date.context_today
            tax_filtered_records = sum(record.tax_depreciation_move_ids
                                       .filtered(lambda rec: rec.date and rec.date <= fields.Date.today())
                                       .mapped("depreciation"))
            record.tax_accumulated_dep = tax_filtered_records
    
    # @api.depends('original_value', 'takeon_accumulated_depreciation', 'salvage_value', 'value_residual', 'children_ids.book_value', 'children_ids.original_value','state')
    @api.depends('x_purch_price', 'original_value', 'takeon_accumulated_depreciation', 'value_residual', 'salvage_value', 'already_depreciated_amount_import', 'children_ids.book_value', 'children_ids.original_value','state')
    def _compute_book_value(self):
        _logger.info("\n\n\t\t _compute_book_value ===================")
        for record in self:
            if record.state == 'close':
                record.book_value = 0.00
            else:
                # record.book_value = record.total_cost - record.salvage_value - record.takeon_accumulated_depreciation - record.value_residual + sum(record.children_ids.mapped('book_value'))
                book_value = record.value_residual + record.salvage_value + sum(record.children_ids.mapped('book_value'))
                if record.depreciation_move_ids:
                    record.book_value = record.x_purch_price + record.x_value_addition - record.value_residual + record.salvage_value + sum(record.children_ids.mapped('book_value'))
                else:
                    record.book_value = record.x_purch_price - record.already_depreciated_amount_import - record.salvage_value - record.takeon_accumulated_depreciation + sum(record.children_ids.mapped('book_value'))

            record.gross_increase_value = sum(record.children_ids.mapped('original_value'))

    # @api.depends('tax_original_value', 'tax_value_residual', 'tax_salvage_value', 'takeon_accumulated_depreciation_tax', 'children_ids.tax_book_value', 'state','tax_accumulated_dep')
    @api.depends('tax_original_value', 'tax_value_residual', 'tax_salvage_value', 'takeon_accumulated_depreciation_tax', 'children_ids.tax_book_value', 'state','tax_accumulated_dep')
    def _compute_tax_book_value(self):
        for record in self:
            if record.state == 'close':
                record.tax_book_value = 0.00
            else:
                # # record.tax_book_value = record.tax_original_value - record.tax_salvage_value - record.takeon_accumulated_depreciation_tax - record.tax_value_residual + sum(record.children_ids.mapped('tax_book_value'))
                # record.tax_book_value = record.tax_original_value - record.tax_accumulated_dep + sum(record.children_ids.mapped('tax_book_value'))
                # # record.tax_book_value = record.tax_original_value - record.tax_salvage_value + record.tax_x_value_addition - record.takeon_accumulated_depreciation_tax - record.tax_value_residual + sum(record.children_ids.mapped('tax_book_value'))
                record.tax_book_value = record.tax_original_value - record.tax_accumulated_dep + sum(record.children_ids.mapped('tax_book_value'))

    @api.depends('original_move_line_ids')
    def _compute_display_account_asset_id(self):
        for record in self:
            if record.original_move_line_ids:
                record.display_account_asset_id = False
            else:
                record.display_account_asset_id = True

    @api.depends('asset_type', 'user_type_id', 'state')
    def _compute_display_model_choice(self):
        for record in self:
            domain = [('state', '=', 'model')]
            if record.user_type_id:
                domain += [('user_type_id', '=', record.user_type_id.id)]
            else:
                domain += [('asset_type', '=', record.asset_type)]
            record.display_model_choice = (
                record.state == 'draft'
                and bool(self.env['account.asset'].search(domain, limit=1))
            )
    
    @api.depends('asset_value_addition_ids', 'asset_value_addition_ids.value_amount', 'asset_value_addition_ids.tax_value_amount')
    def _compute_x_value_addition(self):
        for record in self:
            record.x_value_addition  = 0.00
            record.tax_x_value_addition  = 0.00
            record.value_addition = False
            if record.asset_value_addition_ids:
                record.x_value_addition = sum(record.asset_value_addition_ids.mapped('value_amount'))
                record.tax_x_value_addition = sum(record.asset_value_addition_ids.mapped('tax_value_amount'))
                record.value_addition = True
                
    # @api.depends('asset_revalue_ids', 'asset_revalue_ids.value_amount')
    # def _compute_x_value_revalue(self):
    #     for record in self:
    #         record.x_book_reval  = 0.00
    #         record.value_addition = False
    #         if record.asset_value_addition_ids:
    #             record.x_value_addition = sum(record.asset_value_addition_ids.mapped('value_amount'))
    #             record.tax_x_value_addition = sum(record.asset_value_addition_ids.mapped('tax_value_amount'))
    #             record.value_addition = True

    @api.depends('asset_revalue_ids', 'asset_revalue_ids.value_amount')
    def _compute_value_revaluation(self):
        for record in self:
            record.x_book_reval  = 0.00
            record.value_revaluation = False
            if record.asset_revalue_ids:
                record.x_book_reval = sum(record.asset_revalue_ids.mapped('value_amount'))
                record.value_revaluation = True

    @api.depends('x_purch_price','x_book_reval','asset_revalue_ids.value_amount','x_value_addition')
    def _compute_total_cost_value(self):
         for record in self:
            if record.asset_revalue_ids or record.asset_value_addition_ids:
                record.total_cost = record.x_purch_price + record.x_book_reval + sum(record.asset_value_addition_ids.mapped('value_amount'))
            else:
                record.total_cost = record.x_purch_price + record.x_book_reval + record.x_value_addition

    @api.depends('original_move_line_ids', 'original_move_line_ids.account_id', 'asset_type', 'asset_revalue_ids', 'asset_revalue_ids.value_amount', 'x_purch_price', 'x_book_reval', 'asset_value_addition_ids', 'asset_value_addition_ids.value_amount')
    def _compute_value(self):
        for record in self:
            if record.state=='draft' and record.x_purch_price:
                record.original_value = record.x_purch_price
            if record.asset_revalue_ids or record.asset_value_addition_ids:
                record.original_value = record.x_purch_price + record.x_book_reval + sum(record.asset_value_addition_ids.mapped('value_amount'))
            else:
                misc_journal_id = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', record.company_id.id)], limit=1)
                if not record.original_move_line_ids:
                    record.original_value = record.original_value or False
                    continue
                if any(line.move_id.state == 'draft' for line in record.original_move_line_ids):
                    raise UserError(_("All the lines should be posted"))
                if any(type != record.original_move_line_ids[0].move_id.move_type for type in record.original_move_line_ids.mapped('move_id.move_type')):
                    raise UserError(_("All the lines should be from the same move type"))
                if not record.journal_id:
                    record.journal_id = misc_journal_id
                total_credit = sum(line.credit for line in record.original_move_line_ids)
                total_debit = sum(line.debit for line in record.original_move_line_ids)
                record.original_value = total_credit + total_debit
                if record.account_asset_id.multiple_assets_per_line and len(record.original_move_line_ids) == 1:
                    record.original_value /= max(1, int(record.original_move_line_ids.quantity))
                if (total_credit and total_debit) or record.original_value == 0:
                    raise UserError(_("You cannot create an asset from lines containing credit and debit on the account or with a null amount"))

    @api.depends('original_value', 'asset_revalue_ids', 'asset_revalue_ids.tax_value_amount', 'x_purch_price', 'x_book_reval', 'asset_value_addition_ids', 'asset_value_addition_ids.tax_value_amount','tax_x_value_addition','tax_purch_price')
    def _compute_value_tax(self):
        for record in self:
            if record.asset_revalue_ids or record.asset_value_addition_ids:
                # record.tax_original_value = record.x_purch_price + record.x_book_reval + sum(record.asset_value_addition_ids.mapped('tax_value_amount'))
                record.tax_original_value = record.tax_purch_price  + sum(record.asset_value_addition_ids.mapped('tax_value_amount'))
            else:
                record.tax_original_value = record.tax_purch_price + record.tax_x_value_addition 
                # record.tax_original_value = 0
                
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            self_comp = self.with_company(company_id)
            if vals.get('seq_no', 'New') == 'New':
                vals['seq_no'] = self_comp.env['ir.sequence'].next_by_code('account.asset') or '/'
        return super(AccountAsset, self).create(vals_list)

    @api.depends('parent_id')
    def _entry_add_value_list(self):
        for asset in self:
            res = self.env['asset.value.addition'].search_count([('asset_id', '=', asset.id)])
            asset.add_value_count = res or 0

    @api.depends('parent_id')
    def _entry_revalue_list(self):
        for asset in self:
            res = self.env['asset.revalue'].search_count([('asset_id', '=', asset.id)])
            asset.revalue_count = res or 0

    @api.depends('parent_id')
    def _tax_entry_count(self):
        for asset in self:
            res = self.env['account.asset.tax'].search_count([('asset_id', '=', asset.id)])
            asset.tax_depreciation_entries_count = res or 0

    # @api.depends('tax_acquisition_date', 'tax_depreciation_move_ids', 'tax_method_period', 'company_id')
    # def _compute_tax_first_depreciation_date(self):
    #     for record in self:
    #         # if record.state == "draft":
    #         #     record.tax_first_depreciation_date = ""
    #         # else:
    #             pre_depreciation_date = record.tax_acquisition_date or min(record.tax_depreciation_move_ids.mapped('date'),
    #                                                                     default=record.tax_acquisition_date) or fields.Date.today()
    #             # depreciation_date = pre_depreciation_date + relativedelta(day=31)
    #             depreciation_date = pre_depreciation_date
    #                 # ... or fiscalyear depending the number of period
    #             if record.tax_method_period == '12':
    #                 depreciation_date = depreciation_date + relativedelta(
    #                     month=int(record.company_id.fiscalyear_last_month))
    #                 depreciation_date = depreciation_date + relativedelta(day=record.company_id.fiscalyear_last_day)
    #                 if depreciation_date < pre_depreciation_date:
    #                     depreciation_date = depreciation_date + relativedelta(years=1)
    #             record.tax_first_depreciation_date = depreciation_date
    #         # record.tax_first_depreciation_date = ""

    @api.onchange('x_purch_price')
    def _onchange_x_purch_price(self):
        self.tax_purch_price = self.x_purch_price

    # @api.onchange('new_acquisition_date')
    # def _onchange_new_acquisition_date(self):
    #     self.acquisition_date = self.new_acquisition_date
    
    
    # @api.onchange('new_first_depreciation_date')
    # def _onchange_new_first_depreciation_date(self):
    #     self.first_depreciation_date = self.new_first_depreciation_date
    
    @api.onchange('depreciation_percentage')
    def _onchange_depreciation_percentage(self):
        depreciation_percentage = self.depreciation_percentage
        if depreciation_percentage:
            self.method_number = (1/depreciation_percentage*100)*12
            self.method_period = '1'

    @api.onchange('tax_depreciation_percentage')
    def _onchange_tax_depreciation_percentage(self):
        tax_depreciation_percentage = self.tax_depreciation_percentage
        if tax_depreciation_percentage:
            self.tax_method_number = (1 / tax_depreciation_percentage * 100) * 12
            self.tax_method_period = '1'

    @api.onchange('asset_model')
    def _onchange_asset_model(self):
        model = self.asset_model
        if model:
            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.depreciation_percentage = model.depreciation_percentage
            self.prorata = model.prorata
            self.prorata_date = fields.Date.today()
            self.account_analytic_id = model.account_analytic_id.id
            self.analytic_tag_ids = [(6, 0, model.analytic_tag_ids.ids)]
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id
            self.account_asset_id = model.account_asset_id
            self.tax_method = model.tax_method
            # self.tax_method_number = model.tax_method_number
            self.tax_method_period = model.tax_method_period
            self.tax_method_progress_factor = model.tax_method_progress_factor
            # self.tax_depreciation_percentage = model.tax_depreciation_percentage
            self.tax_prorata = model.tax_prorata
            self.tax_prorata_date = fields.Date.today()
            self.group_id = model.group_id

    def _compute_board_amount(self, computation_sequence, residual_amount, total_amount_to_depr, max_depreciation_nb, starting_sequence, depreciation_date):
        amount = super(AccountAsset, self)._compute_board_amount(computation_sequence, residual_amount, total_amount_to_depr, max_depreciation_nb, starting_sequence, depreciation_date)
        if computation_sequence != max_depreciation_nb:
            if self.method in ('degressive', 'degressive_then_linear'):
                if residual_amount <= 20:
                    amount = residual_amount
        return amount

    def _compute_tax_board_amount(self, computation_sequence, residual_amount, total_amount_to_depr, max_depreciation_nb, starting_sequence, depreciation_date):
        amount = 0
        if computation_sequence == max_depreciation_nb:
            amount = residual_amount
        else:
            if self.tax_method in ('degressive', 'degressive_then_linear'):
                if residual_amount <= 20:
                    amount = residual_amount
                else:
                    amount = residual_amount * self.tax_method_progress_factor
            if self.tax_method in ('linear', 'degressive_then_linear'):
                nb_depreciation = max_depreciation_nb - starting_sequence
                if self.tax_prorata:
                    nb_depreciation -= 1
                linear_amount = min(total_amount_to_depr / nb_depreciation, residual_amount)
                if self.tax_method == 'degressive_then_linear':
                    amount = max(linear_amount, amount)
                else:
                    amount = linear_amount
        return amount

    def _recompute_tax_board(self, tax_depreciation_number, tax_starting_sequence, tax_amount_to_depreciate, tax_depreciation_date):
        self.ensure_one()
        tax_residual_amount = tax_amount_to_depreciate
        move_vals = []
        prorata = self.tax_prorata
        if tax_amount_to_depreciate != 0.0:
            for asset_sequence in range(tax_starting_sequence + 1, tax_depreciation_number + 1):
                amount = self._compute_tax_board_amount(asset_sequence, tax_residual_amount, tax_amount_to_depreciate, tax_depreciation_number, tax_starting_sequence, tax_depreciation_date)
                prorata_factor = 1
                ref = self.name + ' (%s/%s)' % (prorata and asset_sequence - 1 or asset_sequence, self.tax_method_number)
                if prorata and asset_sequence == 1:
                    ref = self.name + ' ' + _('(prorata entry)')
                    first_date = self.tax_prorata_date
                    if int(self.tax_method_period) % 12 != 0:
                        month_days = calendar.monthrange(first_date.year, first_date.month)[1]
                        days = month_days - first_date.day + 1
                        prorata_factor = days / month_days
                    else:
                        total_days = (tax_depreciation_date.year % 4) and 365 or 366
                        days = (self.company_id.compute_fiscalyear_dates(first_date)['date_to'] - first_date).days + 1
                        prorata_factor = days / total_days
                amount = self.currency_id.round(amount * prorata_factor)
                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue
                tax_residual_amount -= amount

                move_vals.append({
                    'depreciation': amount,
                    'asset_id': self.id,
                    'ref': ref,
                    'date': tax_depreciation_date,
                    'depreciable_value': float_round(tax_residual_amount, precision_rounding=self.currency_id.rounding),
                    'cumulative_depreciation': tax_amount_to_depreciate - tax_residual_amount
                })
                _logger.info("tax_depreciation_date..... ",tax_depreciation_date)
                _logger.info("tax_period..... ",int(self.tax_method_period))
                tax_depreciation_date = tax_depreciation_date + relativedelta(months=+int(self.tax_method_period))
                # tax_depreciation_date = date.today() + relativedelta(months=+int(self.tax_method_period))
                # datetime doesn't take into account that the number of days is not the same for each month
                if int(self.tax_method_period) % 12 != 0:
                    max_day_in_month = calendar.monthrange(tax_depreciation_date.year, tax_depreciation_date.month)[1]
                    tax_depreciation_date = tax_depreciation_date.replace(day=max_day_in_month)
        return move_vals

    def compute_tax_depreciation_board(self):
        self.ensure_one()
        existed_tax_depreciation_number = 0
        existed_tax_depreciation_number = len(self.tax_depreciation_move_ids.ids)
        tax_depreciation_number = self.tax_method_number
        if self.tax_prorata:
            tax_depreciation_number += 1
        tax_starting_sequence = 0
        # tax_amount_to_depreciate = self.tax_value_residual
        tax_amount_to_depreciate = self.tax_original_value

        tax_depreciation_date = self.tax_first_depreciation_date
        # tax_depreciation_date = fields.Date.today()

        if existed_tax_depreciation_number:
            tax_depreciation_number = tax_depreciation_number - existed_tax_depreciation_number
            tax_amount_to_depreciate = tax_amount_to_depreciate - sum(self.tax_depreciation_move_ids.mapped('depreciation'))
            tax_depreciation_date = (tax_depreciation_date + relativedelta(months=existed_tax_depreciation_number)) + relativedelta(day=31)

        _logger.info("Inside tax line compute")
        # new added condition
        # commands = [(2, line_id.id, False) for line_id in self.tax_depreciation_move_ids.filtered(lambda x: x.date == 'posted')]
        # new added condition
        _logger.info("tax depriciation date is.....%s",tax_depreciation_date)
        newlines = self._recompute_tax_board(tax_depreciation_number, tax_starting_sequence, tax_amount_to_depreciate, tax_depreciation_date)
        newline_vals_list = []
        for newline_vals in newlines:
            _logger.info("New tax line values.....",newline_vals)
            newline_vals_list.append(newline_vals)
        new_moves = self.env['account.asset.tax'].create(newline_vals_list)
        # change here
        commands = []
        for move in new_moves:
            commands.append((4, move.id))
        return self.write({'tax_depreciation_move_ids': commands})

    def validate(self):
        res = super(AccountAsset, self).validate()
        if not self.tax_depreciation_move_ids:
        # new added condition
        # if self.tax_depreciation_move_ids:
        # new added condition
            self.compute_tax_depreciation_board()
        return res

    def compute_depreciation_board(self):
        self.ensure_one()
        amount_change_ids = self.depreciation_move_ids.filtered(lambda x: x.asset_value_change and not x.reversal_move_id).sorted(key=lambda l: l.date)
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(lambda x: x.state == 'posted' and not x.asset_value_change and not x.reversal_move_id).sorted(key=lambda l: l.date)
        already_depreciated_amount = sum([m.amount_total for m in posted_depreciation_move_ids])

        _logger.info("posted_depreciation_move_ids is %s",posted_depreciation_move_ids)
        _logger.info("posted_depreciation_move_ids is %s",len(posted_depreciation_move_ids))

        existed_depreciation_number = 0
        existed_depreciation_number = len(posted_depreciation_move_ids)

        if self.depreciation_number_import:
            depreciation_number = self.method_number - self.depreciation_number_import
        else:
            depreciation_number = self.method_number - existed_depreciation_number
        if self.prorata:
            depreciation_number += 1
        starting_sequence = 0
        
        _logger.info("original_value is %s",self.original_value)
        _logger.info("salvage_value is %s",self.salvage_value)
        _logger.info("already_depreciated_amount is %s",already_depreciated_amount)
         
        amount_to_depreciate = self.original_value - self.salvage_value - already_depreciated_amount - self.x_book_reval - self.already_depreciated_amount_import


        # check here
        depreciation_date = self.first_depreciation_date
        # if we already have some previous validated entries, starting date is last entry + method period
        if posted_depreciation_move_ids and posted_depreciation_move_ids[-1].date:
            last_depreciation_date = fields.Date.from_string(posted_depreciation_move_ids[-1].date)
            if last_depreciation_date >= depreciation_date:  # in case we unpause the asset
                depreciation_date = (last_depreciation_date + relativedelta(months=+int(self.method_period))) + relativedelta(day=31)
                _logger.info('depreciation_date is %s',depreciation_date)

        commands = [(2, line_id.id, False) for line_id in self.depreciation_move_ids.filtered(lambda x: x.state == 'draft')]
        newlines = self._recompute_board(depreciation_number, starting_sequence, amount_to_depreciate, depreciation_date, already_depreciated_amount, amount_change_ids)
        newline_vals_list = []
        for newline_vals in newlines:
            # no need of amount field, as it is computed and we don't want to trigger its inverse function
            del(newline_vals['amount_total'])
            newline_vals_list.append(newline_vals)
        new_moves = self.env['account.move'].create(newline_vals_list)
        for move in new_moves:
            commands.append((4, move.id))
        _logger.info("before tax line unlink")
        if self.tax_depreciation_move_ids:
            _logger.info("if tax_depreciation_move_ids exists")
            if self.env.context.get('asset_value_date_addition', False) and self.env.context.get('asset_value_addition_tax_value_amount', 0.00) > 0.00:
                tax_depreciation_move_ids_to_be_deleted = self.tax_depreciation_move_ids.filtered(lambda rec: rec.date >= self.env.context.get('asset_value_date_addition', False))
                if tax_depreciation_move_ids_to_be_deleted:
                    tax_depreciation_move_ids_to_be_deleted.unlink()
                    _logger.info('where tax amoutn > 0')
            else:
                # self.tax_depreciation_move_ids.unlink()
                if self.env.context.get('asset_value_date_addition', False):
                    tax_depreciation_move_ids_to_be_deleted = self.tax_depreciation_move_ids.filtered(lambda rec: rec.date >= self.env.context.get('asset_value_date_addition', False))
                    if tax_depreciation_move_ids_to_be_deleted:
                        tax_depreciation_move_ids_to_be_deleted.unlink()
                        _logger.info('where tax amoutn < 0')
                else:
                    self.tax_depreciation_move_ids.unlink()
                
        _logger.info("before tax line compute call")
        self.compute_tax_depreciation_board()
        res = self.write({'depreciation_move_ids': commands})
        if self.state == 'open':
            self.depreciation_move_ids.filtered(lambda x: x.state == 'draft')._post()
        return res

    # functionality to confirm the asset in batch
    def compute_batch_asset(self):
        asset_ids = []
        active_ids = self.env.context.get('active_ids',[])
        asset_id = self.env['account.asset'].search([('id','in',active_ids)])
        for rec in asset_id:
            if rec.state != 'draft':
                raise UserError(_("Kindly select the Assets in Draft state"))
            else:
                asset_ids.append(rec.id)
        vals = ({'default_asset_ids':asset_ids})
        return {
            'name':"Asset Batch Confirm",
            'type': 'ir.actions.act_window', 
            'view_type': 'form', 
            'view_mode': 'form',
            'res_model': 'account.asset.batch', 
            'target': 'new', 
            'context': vals
            }

    def action_asset_value_addition(self):
        """ Returns an action opening the asset modification wizard.
        """
        self.ensure_one()
        value_addition_id = self.env['asset.value.addition'].search([('name','=',False),('asset_id','=',self.id)])
        if value_addition_id:
            for line in value_addition_id:
                line.unlink()
        new_wizard = self.env['asset.value.addition'].create({
            'asset_id': self.id,
            'currency_id':self.currency_id.id,
            'analytic_account_id':self.account_analytic_id.id,
            'account_asset_id':self.account_asset_id.id,
            'account_asset_counterpart_id':self.company_id.value_clearing_account.id
        })
        return {
            'name': _('Addition'),
            'view_mode': 'form',
            'res_model': 'asset.value.addition',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }

    def open_value_entries(self):
        return {
            'name': _('Value Additions'),
            'view_mode': 'tree,form',
            'res_model': 'asset.value.addition',
            'views': [(self.env.ref('enabling_account_asset.asset_value_addition_tree').id, 'tree'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('asset_id', '=', self.id)],
            'context': dict(self._context, create=False),
        }

    def action_asset_revalue(self):
        """ Returns an action opening the asset modification wizard.
        """
        self.ensure_one()
        revalue_id = self.env['asset.revalue'].search([('name','=',False),('asset_id','=',self.id)])
        if revalue_id:
            for line in revalue_id:
                line.unlink()
        new_wizard = self.env['asset.revalue'].create({
            'asset_id': self.id,
            'book_reval':self.x_book_reval,
            'currency_id':self.currency_id.id,
            'analytic_account_id':self.account_analytic_id.id,
            'account_asset_id':self.account_asset_id.id,
            'account_asset_counterpart_id':self.company_id.revalue_clearing_account.id
        })
        return {
            'name': _('Revalue'),
            'view_mode': 'form',
            'res_model': 'asset.revalue',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }
    def open_revalue_entries(self):
        return {
            'name': _('Revalue'),
            'view_mode': 'tree,form',
            'res_model': 'asset.revalue',
            'views': [(self.env.ref('enabling_account_asset.asset_revalue_tree').id, 'tree'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('asset_id', '=', self.id)],
            'context': dict(self._context, create=False),
        }

    def action_set_to_close(self):
        """ Returns an action opening the asset pause wizard."""
        self.ensure_one()
        new_wizard = self.env['account.asset.sell'].create({
            'asset_id': self.id,
            'analytic_account_id':self.account_analytic_id.id,
        })
        return {
            'name': _('Sell Asset'),
            'view_mode': 'form',
            'res_model': 'account.asset.sell',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
        }

    def set_to_close(self, invoice_line_id, loss_account_id, gain_account_id, analytic_account_id, date):
        self.ensure_one()
        disposal_date = date or fields.Date.today()
        # disposal_date = date
        _logger.info("disposal date is......",disposal_date)
        gain_account_id = gain_account_id
        loss_account_id = loss_account_id
        if invoice_line_id and self.children_ids.filtered(lambda a: a.state in ('draft', 'open') or a.value_residual > 0):
            raise UserError(_("You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."))
        full_asset = self + self.children_ids
        move_ids = full_asset._get_disposal_moves([invoice_line_id] * len(full_asset), disposal_date, loss_account_id, gain_account_id, analytic_account_id)
        full_asset.write({'state': 'close'})
        # Deleting unwanted tax depriciation board lines
        to_be_deleted_tax_depreciation_move_ids = self.tax_depreciation_move_ids.filtered(lambda rec: rec.date > disposal_date)
        if to_be_deleted_tax_depreciation_move_ids:
            to_be_deleted_tax_depreciation_move_ids.unlink()
        if move_ids:
            return self._return_disposal_view(move_ids)

    def _get_disposal_moves(self, invoice_line_ids, disposal_date, loss_account_id, gain_account_id, analytic_account_id):
        def get_line(asset, amount, account):
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)],
                'currency_id': current_currency.id,
                'amount_currency': -asset.value_residual,
            })

        move_ids = []
        assert len(self) == len(invoice_line_ids)
        for asset, invoice_line_id in zip(self, invoice_line_ids):
            posted_moves = asset.depreciation_move_ids.filtered(lambda x: (
                not x.reversal_move_id
                and x.state == 'posted'
            ))
            if posted_moves and disposal_date < max(posted_moves.mapped('date')):
                if invoice_line_id:
                    raise UserError('There are depreciation posted after the invoice date (%s).\nPlease revert them or change the date of the invoice.' % disposal_date)
                else:
                    raise UserError('There are depreciation posted in the future, please revert them.')
            account_analytic_id = analytic_account_id or asset.account_analytic_id
            analytic_tag_ids = asset.analytic_tag_ids
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            prec = company_currency.decimal_places
            
            # change filter to remove records less than disposal date
            # unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(lambda x: x.state == 'draft')
            # _logger.info("disposal_date is....",disposal_date)
            # print("disposal_date is ......", disposal_date)
            unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(lambda x: x.date > disposal_date)

            old_values = {
                'method_number': asset.method_number,
            }

            # Remove all unposted depr. lines
            commands = [(2, line_id.id, False) for line_id in unposted_depreciation_move_ids]

            # Create a new depr. line with the residual amount and post it
            asset_sequence = len(asset.depreciation_move_ids) - len(unposted_depreciation_move_ids) + 1

            initial_amount = asset.total_cost #asset.original_value
            initial_account = asset.original_move_line_ids.account_id if len(asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id
            depreciation_moves = asset.depreciation_move_ids.filtered(lambda r: r.state == 'posted' and not (r.reversal_move_id and r.reversal_move_id[0].state == 'posted'))
 
            depreciated_amount = -asset.value_residual
            depreciation_account = asset.account_depreciation_id
            invoice_amount = copysign(invoice_line_id.price_subtotal, -initial_amount)
            invoice_account = invoice_line_id.account_id
            difference = -initial_amount - depreciated_amount - invoice_amount
            # difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            difference_account = gain_account_id if difference > 0 else loss_account_id
            line_datas = [(initial_amount, initial_account), (depreciated_amount, depreciation_account), (invoice_amount, invoice_account), (difference, difference_account)]
            if not invoice_line_id:
                del line_datas[2]
            vals = {
                'asset_id': asset.id,
                'ref': asset.name + ': ' + (_('Disposal') if not invoice_line_id else _('Sale')),
                'asset_remaining_value': 0,
                'asset_depreciated_value': max(asset.depreciation_move_ids.filtered(lambda x: x.state == 'posted'), key=lambda x: x.date, default=self.env['account.move']).asset_depreciated_value,
                'date': disposal_date,
                'journal_id': asset.journal_id.id,
                'line_ids': [get_line(asset, amount, account) for amount, account in line_datas if account],
            }
            commands.append((0, 0, vals))
            asset.write({'depreciation_move_ids': commands, 'method_number': asset_sequence})
            if asset.depreciation_move_ids:
                max(asset.depreciation_move_ids, key=lambda x: x.date, default=self.env['account.move']).asset_depreciated_value += max(asset.depreciation_move_ids, key=lambda x: x.date, default=self.env['account.move']).amount_total
            tracked_fields = self.env['account.asset'].fields_get(['method_number'])
            changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
            if changes:
                asset.message_post(body=_('Asset sold or disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
            move_ids += self.env['account.move'].search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids

        return move_ids
               
class AccountAssetTax(models.Model):
    _name = 'account.asset.tax'

    ref = fields.Char(string='Reference')
    date = fields.Date(string='Depreciation Date')
    depreciation = fields.Monetary(string='Depreciation')
    cumulative_depreciation = fields.Monetary(string='Cumulative Depreciation')
    depreciable_value = fields.Monetary(string='Depreciable Value')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True,
                                  default=lambda self: self.env.company.currency_id.id)
    asset_id = fields.Many2one('account.asset', string='Asset', index=True, ondelete='cascade', copy=False)
    company_id = fields.Many2one(related="asset_id.company_id", string="Company", readonly=True, store=True)

class EnablingEmployee(models.Model):
    _name = 'enabling.employee'

    name = fields.Char("Name")

class AssetValueAddition(models.Model):
    _name = 'asset.value.addition'

    @api.model
    def _valid_field_parameter(self, field, name):
        return name in ['tracking'] or super()._valid_field_parameter(field, name)

    asset_id = fields.Many2one(string="Asset", comodel_name='account.asset', required=True, help="The asset to be modified by this wizard", ondelete="cascade")
    company_id = fields.Many2one(related="asset_id.company_id", string="Company", readonly=True, store=True)
    name = fields.Char('Reason')
    date = fields.Date(default=fields.Date.context_today, string='Date')
    account_asset_id = fields.Many2one('account.account', string="Asset Account")
    account_asset_counterpart_id = fields.Many2one('account.account', string="Clearing Account")
    value_amount = fields.Float(string="Addition Book Amt")
    tax_value_amount = fields.Float(string="Addition Tax Amt")
    analytic_account_id = fields.Many2one('account.analytic.account',string="Analytic Account")
    currency_id = fields.Many2one('res.currency',string='Currency')
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
        ], string='Status', required=True, copy=False, tracking=True,
        default='draft')
    journal_id = fields.Many2one('account.move',string="Journal",readonly=True)

    # @api.onchange('value_amount')
    # def _onchange_value_amount(self):
    #      for line in self:
    #          if line.value_amount:
    #          line.tax_value_amount = line.value_amount

    def modify(self):
        for asset in self:
            balance = self.value_amount
            move_vals = {
                    'date': asset.date,
                    'ref':asset.asset_id.name,
                    'journal_id': asset.asset_id.journal_id.id,
                    'currency_id': asset.asset_id.journal_id.currency_id.id or asset.asset_id.company_id.currency_id.id,
                    'line_ids': [
                    (0, 0, {
                        'name': asset.name,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'analytic_account_id':asset.analytic_account_id.id,
                        'account_id': asset.account_asset_id.id,
                    }),
                    (0, 0, {
                        'name': asset.name,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'analytic_account_id':asset.analytic_account_id.id,
                        'account_id': asset.account_asset_counterpart_id.id,
                    }),
                ],}
            journal = self.env['account.move'].create(move_vals)
            self.journal_id = journal
            self.state = 'posted'
        value_addition_id = self.env['asset.value.addition'].search([('journal_id','=',False),('asset_id','=',self.asset_id.id)])
        if value_addition_id:
            for line in value_addition_id:
                line.unlink()
        self.asset_id.with_context(asset_value_date_addition=self.date, asset_value_addition_tax_value_amount=self.tax_value_amount).compute_depreciation_board()
        return

class AssetRevalue(models.Model):
    _name = 'asset.revalue'

    @api.model
    def _valid_field_parameter(self, field, name):
        return name in ['tracking'] or super()._valid_field_parameter(field, name)

    asset_id = fields.Many2one(string="Asset", comodel_name='account.asset', required=True, help="The asset to be modified by this wizard", ondelete="cascade")
    company_id = fields.Many2one(related="asset_id.company_id", string="Company", readonly=True, store=True)
    name = fields.Char('Reason')
    date = fields.Date(default=fields.Date.context_today, string='Date')
    account_asset_id = fields.Many2one('account.account', string="Asset Account")
    account_asset_counterpart_id = fields.Many2one('account.account', string="Clearing Account")
    value_amount = fields.Float(string="Revaluation Amount")
    tax_value_amount = fields.Float(string="Addition Tax Amt")
    analytic_account_id = fields.Many2one('account.analytic.account',string="Analytic Account")
    currency_id = fields.Many2one('res.currency',string='Currency')
    book_reval = fields.Float(string="Revaluation")
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
        ], string='Status', required=True, copy=False, tracking=True,
        default='draft')
    journal_id = fields.Many2one('account.move',string="Journal",readonly=True)

    def modify(self):
        for asset in self:
            balance = self.value_amount
            move_vals = {
                    'date': asset.date,
                    'ref':asset.asset_id.name,
                    'journal_id': asset.asset_id.journal_id.id,
                    'currency_id': asset.asset_id.journal_id.currency_id.id or asset.asset_id.company_id.currency_id.id,
                    'line_ids': [
                    (0, 0, {
                        'name': asset.name,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'analytic_account_id': asset.analytic_account_id.id,
                        'account_id': asset.account_asset_id.id,
                    }),
                    (0, 0, {
                        'name': asset.name,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'analytic_account_id':asset.analytic_account_id.id,
                        'account_id': asset.account_asset_counterpart_id.id,
                    }),

                ],}
            journal = self.env['account.move'].create(move_vals)
            self.journal_id = journal
            self.state = 'posted'
        revalue_id = self.env['asset.revalue'].search([('journal_id','=',False),('asset_id','=',self.asset_id.id)])
        if revalue_id:
            for line in revalue_id:
                line.unlink()
        self.asset_id.write({
            'x_book_reval': self.value_amount + self.book_reval})
        return


class AccountAssetGroup(models.Model):
    _inherit = 'account.asset.group'

    name = fields.Char(string="Group Name", required=True)
