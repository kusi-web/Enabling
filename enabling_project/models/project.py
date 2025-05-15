# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _


class TaskItem(models.Model):
    _name = "project.task.item"
    _description = "Task Item"

    name = fields.Char(string='Task Name')
    account_id = fields.Many2one('account.account', string='GL Account',
                                 index=True, ondelete="cascade",
                                 domain="[('deprecated', '=', False),('is_off_balance', '=', False)]",
                                 check_company=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    budget = fields.Monetary(string='Budget')
    old_invoices = fields.Monetary(string='Old Invoices')
    invoiced = fields.Monetary(string='Invoiced', compute='_compute_invoice_amount')
    draft_invoices = fields.Monetary(string='Draft Invoices', compute='_compute_invoice_amount')
    gl_journals = fields.Monetary(string='GL Journals', compute='_compute_invoice_amount')
    total_excl_draft = fields.Monetary(string='Total Excl Draft', compute='_compute_total')
    total_incl_draft = fields.Monetary(string='Total Incl Draft', compute='_compute_total')
    budget_available = fields.Monetary(string='Budget Available', compute='_compute_budget_available')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True,
                                  default=lambda self: self.env.company.currency_id.id)
    task_id = fields.Many2one('project.task')

    @api.depends('old_invoices', 'invoiced', 'gl_journals', 'draft_invoices')
    def _compute_total(self):
        for record in self:
            record.total_excl_draft = record.old_invoices + record.invoiced + record.gl_journals
            record.total_incl_draft = record.old_invoices + record.invoiced + record.gl_journals + record.draft_invoices

    @api.depends('budget', 'old_invoices', 'invoiced', 'draft_invoices', 'gl_journals')
    def _compute_budget_available(self):
        for record in self:
            record.budget_available = record.budget - record.old_invoices - record.invoiced - record.draft_invoices - record.gl_journals

    @api.depends('budget')
    def _compute_invoice_amount(self):
        for record in self:
            move_obj = self.env['account.move']
            moveline_obj = self.env['account.move.line']

            move_bills_posted = move_obj.search(
                [('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '=', 'posted')])
            move_bills_posted_lines = moveline_obj.search(
                [('move_id', 'in', move_bills_posted.ids), ('task_line_id', '=', record.id)])
            record.invoiced = sum(move_bills_posted_lines.mapped('price_subtotal'))

            move_bills_draft = move_obj.search(
                [('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '=', 'draft')])
            move_bills_draft_lines = moveline_obj.search(
                [('move_id', 'in', move_bills_draft.ids), ('task_line_id', '=', record.id)])
            record.draft_invoices = sum(move_bills_draft_lines.mapped('price_subtotal'))

            move_entries_posted = self.env['account.move'].search(
                [('move_type', '=', 'entry'), ('state', '=', 'posted')])
            move_entries_posted_lines = self.env['account.move.line'].search(
                [('move_id', 'in', move_entries_posted.ids), ('task_line_id', '=', record.id)])
            record.gl_journals = sum(move_entries_posted_lines.mapped('balance'))


class Task(models.Model):
    _inherit = "project.task"

    task_item_ids = fields.One2many('project.task.item', 'task_id', string='Task Items')
    vendor_bills_count = fields.Integer(compute='_compute_vendor_bills_count', string='Vendor Bills')
    journals_count = fields.Integer(compute='_compute_journals_count', string='Journals')

    def _compute_vendor_bills_count(self):
        for record in self:
            moves = self.env['account.move'].search([('move_type', 'in', ('in_invoice', 'in_refund'))])
            record.vendor_bills_count = self.env['account.move.line'].search_count(
                [('move_id', 'in', moves.ids), ('task_id', '=', record.id)])

    def _compute_journals_count(self):
        for record in self:
            moves = self.env['account.move'].search([('move_type', '=', 'entry')])
            record.journals_count = self.env['account.move.line'].search_count(
                [('move_id', 'in', moves.ids), ('task_id', '=', record.id)])

    def action_view_task_vendor_bills(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("enabling_project.act_task_2_move_line_in_invoice")
        moves = self.env['account.move'].search([('move_type', 'in', ('in_invoice', 'in_refund'))])
        lines = self.env['account.move.line'].search([('move_id', 'in', moves.ids), ('task_id', '=', self.id)])
        action['domain'] = [('id', 'in', lines.ids)]
        return action

    def action_view_task_journals(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("enabling_project.act_task_2_move_line_journal_in_invoice")
        moves = self.env['account.move'].search([('move_type', '=', 'entry')])
        lines = self.env['account.move.line'].search([('move_id', 'in', moves.ids), ('task_id', '=', self.id)])
        action['domain'] = [('id', 'in', lines.ids)]
        return action


class Project(models.Model):
    _inherit = "project.project"

    vendor_bills_count = fields.Integer(compute='_compute_vendor_bills_count', string='Vendor Bills')
    journals_count = fields.Integer(compute='_compute_journals_count', string='Journals')

    def _compute_vendor_bills_count(self):
        for record in self:
            moves = self.env['account.move'].search([('move_type', 'in', ('in_invoice', 'in_refund'))])
            record.vendor_bills_count = self.env['account.move.line'].search_count([('move_id', 'in', moves.ids), ('project_id', '=', record.id)])

    def _compute_journals_count(self):
        for record in self:
            moves = self.env['account.move'].search([('move_type', '=', 'entry')])
            record.journals_count = self.env['account.move.line'].search_count([('move_id', 'in', moves.ids), ('project_id', '=', record.id)])

    def action_view_project_vendor_bills(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("enabling_project.act_project_2_move_line_in_invoice")
        moves = self.env['account.move'].search([('move_type', 'in', ('in_invoice', 'in_refund'))])
        lines = self.env['account.move.line'].search([('move_id', 'in', moves.ids), ('project_id', '=', self.id)])
        action['domain'] = [('id', 'in', lines.ids)]
        return action

    def action_view_project_journals(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("enabling_project.act_project_2_move_line_journal_in_invoice")
        moves = self.env['account.move'].search([('move_type', '=', 'entry')])
        lines = self.env['account.move.line'].search([('move_id', 'in', moves.ids), ('project_id', '=', self.id)])
        action['domain'] = [('id', 'in', lines.ids)]
        return action
