# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import format_date
import copy
import binascii
import struct
import time
import itertools
import logging
from itertools import groupby
from collections import defaultdict
_logger = logging.getLogger(__name__)

MAX_NAME_LENGTH = 50


class assets_tax_report(models.Model):
    _inherit = 'account.report'
    _description = 'Account Assets Tax Report'
    _name = 'account.assets.tax.report'
    
    section_report_ids = fields.Many2many('account.report.section', 
        'account_assets_tax_report_section_rel', 'report_id', 'section_id', 
        string='Sections')
    section_main_report_ids = fields.Many2many('account.report.section',
        'account_assets_tax_main_report_section_rel', 'report_id', 'section_id',
        string='Main Report Sections')

    def _valid_field_parameter(self, field, name):
        return name in ['tree_invisible', 'tracking'] or super()._valid_field_parameter(field, name)

    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = fields.Boolean(string='All Entries', default=False)
    filter_hierarchy = fields.Boolean(string='Hierarchy', default=True)
    filter_unfold_all = fields.Boolean(string='Unfold All', default=True)

    def _get_report_name(self):
        return _('Depreciation Tax Table Report')

    @api.model
    def _get_singleton_report(self):
        """Get a singleton report record, creating it if necessary."""
        report = self.env.ref('enabling_account_asset.account_assets_tax_report', raise_if_not_found=False)
        if not report:
            existing_report = self.search([], limit=1)
            report = existing_report or self.create({
                'name': 'Assets Tax Report',
                'filter_unfold_all': True,
                'filter_hierarchy': True,
            })
        return report

    def get_header(self, options):
        start_date = format_date(self.env, options['date']['date_from'])
        end_date = format_date(self.env, options['date']['date_to'])
        return [
            [
                {'name': ''},
                {'name': _('Assets'), 'colspan': 7},
                {'name': _('Cost'), 'colspan': 4},
                {'name': _('Depreciation'), 'colspan': 4},
                {'name': _('Net Book Value')},
            ],
            [
                {'name': ''},  # Description
                {'name': _('Acquisition Date'), 'class': 'text-center'},  # Assets
                {'name': _('Purchase Price'), 'class': 'text-center'},
                {'name': _('Total Accumulated Depreciation'), 'class': 'number'},
                {'name': _('Total Additions'), 'class': 'number'},
                {'name': _('Total Disposals'), 'class': 'number'},
                {'name': _('Rate'), 'class': 'number', 'title': _('In percent.<br>For a linear method, the depreciation rate is computed per year.<br>For a declining method, it is the declining factor'), 'data-toggle': 'tooltip'},
                {'name': _('Total Net Book Value'), 'class': 'number'},
                # {'name': _('First Depreciation'), 'class': 'text-center'},
                # {'name': _('Method'), 'class': 'text-center'},
                {'name': start_date, 'class': 'number'},  # Cost
                {'name': _('Current Period Additions'), 'class': 'number'},
                {'name': _('Current Period Disposals'), 'class': 'number'},
                {'name': end_date, 'class': 'number'},
                {'name': start_date, 'class': 'number'},  # Depreciation
                {'name': _('Current Period Depreciation'), 'class': 'number'},
                {'name': _('Disposals'), 'class': 'number'},
                {'name': end_date, 'class': 'number'},
                {'name': '', 'class': 'number'},  # NBV
            ],
        ]

    @api.model
    def _init_filter_hierarchy(self, options, previous_options=None):
        # overwrite because we don't depend on account.group
        if self.filter_hierarchy is not None:
            if previous_options and 'hierarchy' in previous_options:
                options['hierarchy'] = previous_options['hierarchy']
            else:
                options['hierarchy'] = self.filter_hierarchy

    def get_account_codes(self, account):
        return [(name, name) for name in self._get_account_group_with_company(account.code, account.company_id.id)[1:]]

    def _get_account_group(self, account_code, parent_group=None, group_dict=None):
        """ Get the list of parent groups for this account
        return: list containing the main group key, then the name of every group
                for this account, beginning by the more general, until the
                name of the account itself.
            This method is deprecated. Call instead _get_account_group_with_company
        """
        return self._get_account_group_with_company(account_code, self.env.company.id, parent_group, group_dict)

    def _with_context_company2code2account(self):
        if self.env.context.get('company2code2account') is not None:
            return self

        company2code2account = defaultdict(dict)
        for account in self.env['account.account'].search([]):
            company2code2account[account.company_id.id][account.code] = account

        return self.with_context(company2code2account=company2code2account)

    def _get_account_group_with_company(self, account_code, company_id, parent_group=None, group_dict=None):
        """ Get the list of parent groups for this account
        return: list containing the main group key, then the name of every group
                for this account, beginning by the more general, until the
                name of the account itself.
        """

        if not account_code:
            # This is used if there is no account_asset_id
            account_code = '##'
        group_dict = group_dict or self.env['account.report']._get_account_groups_for_asset_report()
        self = self._with_context_company2code2account()
        account_id = self.env.context['company2code2account'].get(company_id, {}).get(account_code)
        account_suffix = [] if parent_group else [account_id.display_name if account_id else _("No asset account")]
        for k, v in group_dict.items():
            key_split = k.split('-')
            account_code_short = account_code[:len(str(key_split[0]))]
            if not v.get('children') and account_code_short == k:
                return (parent_group or [k]) + [v['name']] + account_suffix
            elif v.get('children') and key_split[0] <= account_code_short <= key_split[1]:
                return self._get_account_group_with_company(
                    account_code_short,
                    company_id,
                    (parent_group or [k]) + [v['name']],
                    v['children']
                ) + account_suffix
        return (parent_group or [account_code[:2]]) + account_suffix

    def _get_rate_cached(self, from_currency, to_currency, company, date, cache):
        if from_currency == to_currency:
            return 1
        key = (from_currency, to_currency, company, date)
        if key not in cache:
            cache[key] = self.env['res.currency']._get_conversion_rate(*key)
        return cache[key]

    def _get_lines(self, options, line_id=None):
        self = self._with_context_company2code2account()
        options['self'] = self
        lines = []
        total = [0] * 14
        asset_lines = self._get_assets_lines(options)
        curr_cache = {}

        for company_id, company_asset_lines in groupby(asset_lines, key=lambda x: x['company_id']):
            parent_lines = []
            children_lines = defaultdict(list)
            company = self.env['res.company'].browse(company_id)
            company_currency = company.currency_id
            for al in company_asset_lines:
                if al['parent_id']:
                    children_lines[al['parent_id']] += [al]
                else:
                    parent_lines += [al]
            for al in parent_lines:
                if al['asset_method'] == 'linear' and al['asset_method_number']:  # some assets might have 0 depreciations because they dont lose value
                    asset_depreciation_rate = ('{:.2f} %').format((100.0 / al['asset_method_number']) * (12 / int(al['asset_method_period'])))
                elif al['asset_method'] == 'linear':
                    asset_depreciation_rate = ('{:.2f} %').format(0.0)
                else:
                    asset_depreciation_rate = ('{:.2f} %').format(float(al['asset_method_progress_factor']) * 100)

                asset_depreciation_rate = ('{:.2f} %').format(al['asset_depreciation_percentage'])

                al_currency = self.env['res.currency'].browse(al['asset_currency_id'])
                al_rate = self._get_rate_cached(al_currency, company_currency, company, al['asset_acquisition_date'], curr_cache)

                # depreciation_opening = company_currency.round(al['depreciated_start'] * al_rate) - company_currency.round(al['depreciation'] * al_rate)
                depreciation_closing = company_currency.round(al['depreciated_end'] * al_rate)
                asset_x_value_addition = company_currency.round((al['asset_x_value_addition'] or 0.00) * al_rate)
                asset_x_value_addition_current = company_currency.round((al['asset_x_value_addition_current'] or 0.00) * al_rate)
                asset_x_value_addition_before = company_currency.round((al['asset_x_value_addition_before'] or 0.00) * al_rate)
                asset_tax_purch_price = company_currency.round((al['asset_tax_purch_price'] or 0.00) * al_rate)
                # asset_value_residual = - company_currency.round((al['asset_value_residual'] or 0.00) * al_rate) 
                asset_total_depreciation = company_currency.round((al['asset_total_depreciation'] or 0.00) * al_rate) 
                depreciation_add = company_currency.round((al['asset_total_depreciation_current'] or 0.00) * al_rate) 
                depreciation_opening = company_currency.round((al['asset_total_depreciation_before'] or 0.00) * al_rate) 
                
                asset_total_disposals = 0.0
                # if al['asset_state'] == 'close':
                #     asset_total_disposals = company_currency.round(al['asset_original_value'] * al_rate)
                    
                depreciation_minus = 0.0
                
                opening = (al['asset_acquisition_date'] or al['asset_date']) < fields.Date.to_date(options['date']['date_from'])
                # asset_opening = company_currency.round(al['asset_original_value'] * al_rate) if opening else 0.0
                asset_add = 0.0
                asset_minus = 0.0

                if al['asset_acquisition_date'] and al['asset_acquisition_date'] >= fields.Date.to_date(options['date']['date_from']) and al['asset_acquisition_date'] <= fields.Date.to_date(options['date']['date_to']):
                    asset_add = asset_tax_purch_price
                
                asset_opening = asset_x_value_addition_before
                if al['asset_acquisition_date'] and al['asset_acquisition_date'] < fields.Date.to_date(options['date']['date_from']):
                    asset_opening +=  asset_tax_purch_price
                asset_add = asset_add + asset_x_value_addition_current

                for child in children_lines[al['asset_id']]:
                    child_currency = self.env['res.currency'].browse(child['asset_currency_id'])
                    child_rate = self._get_rate_cached(child_currency, company_currency, company, child['asset_acquisition_date'], curr_cache)

                    # depreciation_opening += company_currency.round(child['depreciated_start'] * child_rate) - company_currency.round(child['depreciation'] * child_rate)
                    depreciation_closing += company_currency.round(child['depreciated_end'] * child_rate)
                    # asset_value_residual -= company_currency.round(child['asset_value_residual'] * child_rate)
                    asset_total_depreciation += company_currency.round(child['asset_total_depreciation'] * child_rate)
                    depreciation_add += company_currency.round(child['asset_total_depreciation_current'] * child_rate)
                    depreciation_opening += company_currency.round(child['asset_total_depreciation_before'] * child_rate)
                    
                    # if child['asset_state'] == 'close':
                    #     asset_total_disposals += company_currency.round(child['asset_original_value'] * child_rate) 
                        
                    opening = (child['asset_acquisition_date'] or child['asset_date']) < fields.Date.to_date(options['date']['date_from'])
                    # asset_opening += company_currency.round(child['asset_original_value'] * child_rate) if opening else 0.0
                    asset_opening += company_currency.round(child['asset_x_value_addition_before'] * child_rate)
                    if child['asset_acquisition_date'] and child['asset_acquisition_date'] < fields.Date.to_date(options['date']['date_from']):
                        asset_opening += company_currency.round(child['asset_tax_purch_price'] * child_rate)
                    
                    child_asset_add = 0.0
                    if child['asset_acquisition_date'] and child['asset_acquisition_date'] >= fields.Date.to_date(options['date']['date_from']) and child['asset_acquisition_date'] <= fields.Date.to_date(options['date']['date_to']):
                        child_asset_add = company_currency.round(child['asset_tax_purch_price'] * child_rate)
                    child_asset_add = child_asset_add + company_currency.round((child['asset_x_value_addition_current'] or 0.00) * child_rate)
                    asset_add += child_asset_add 

                if al['asset_disposal_date'] and al['asset_disposal_date'] >= fields.Date.to_date(options['date']['date_from']) and al['asset_disposal_date'] <= fields.Date.to_date(options['date']['date_to']):
                    asset_minus = asset_opening + asset_add
                    depreciation_minus = depreciation_opening + depreciation_add
                    
                # depreciation_add = depreciation_closing - depreciation_opening
                depreciation_closing = depreciation_opening + depreciation_add - depreciation_minus
                asset_closing = asset_opening + asset_add - asset_minus 

                # if al['asset_state'] == 'close' and al['asset_disposal_date'] and al['asset_disposal_date'] <= fields.Date.to_date(options['date']['date_to']):
                #     depreciation_minus = depreciation_closing
                    # depreciation_opening and depreciation_add are computed from first_move (assuming it is a depreciation move),
                    # but when previous condition is True and first_move and last_move are the same record, then first_move is not a
                    # depreciation move.
                    # In that case, depreciation_opening and depreciation_add must be corrected.
                    # if al['first_move_id'] == al['last_move_id']:
                    #     depreciation_opening = depreciation_closing
                    #     depreciation_add = 0
                    # depreciation_closing = 0.0
                    # asset_minus = asset_closing
                    # asset_closing = 0.0

                asset_gross = asset_closing - depreciation_closing
                if al['asset_state'] == 'close':
                    asset_total_disposals = asset_tax_purch_price + asset_x_value_addition - asset_total_depreciation
                total_net_book_value = asset_tax_purch_price + asset_x_value_addition - asset_total_depreciation - asset_total_disposals

                total = [x + y for x, y in zip(total, [asset_tax_purch_price, asset_total_depreciation, asset_x_value_addition, asset_total_disposals, total_net_book_value, asset_opening, asset_add, asset_minus, asset_closing, depreciation_opening, depreciation_add, depreciation_minus, depreciation_closing, asset_gross])]

                id = "_".join([self._get_account_group_with_company(al['account_code'], al['company_id'])[0], str(al['asset_id'])])
                name = str(al['asset_name'])
                line = {
                    'id': id,
                    'level': 1,
                    'name': name if self._context.get('print_mode') or len(name) < MAX_NAME_LENGTH else name[:MAX_NAME_LENGTH - 2] + '...',
                    'columns': [
                        # Assets
                        {'name': al['asset_acquisition_date'] and format_date(self.env, al['asset_acquisition_date']) or '', 'no_format_name': ''},  
                        {'name': self.format_value(asset_tax_purch_price), 'no_format_name': asset_tax_purch_price},
                        {'name': self.format_value(asset_total_depreciation), 'no_format_name': asset_total_depreciation},
                        {'name': self.format_value(asset_x_value_addition), 'no_format_name': asset_x_value_addition},
                        {'name': self.format_value(asset_total_disposals), 'no_format_name': asset_total_disposals},
                        {'name': asset_depreciation_rate, 'no_format_name': ''},
                        {'name': self.format_value(total_net_book_value), 'no_format_name': total_net_book_value},

                        # Cost
                        {'name': self.format_value(asset_opening), 'no_format_name': asset_opening},  # Assets
                        {'name': self.format_value(asset_add), 'no_format_name': asset_add},
                        {'name': self.format_value(asset_minus), 'no_format_name': asset_minus},
                        {'name': self.format_value(asset_closing), 'no_format_name': asset_closing},

                        # Depreciation
                        {'name': self.format_value(depreciation_opening), 'no_format_name': depreciation_opening},  # Depreciation
                        {'name': self.format_value(depreciation_add), 'no_format_name': depreciation_add},
                        {'name': self.format_value(depreciation_minus), 'no_format_name': depreciation_minus},
                        {'name': self.format_value(depreciation_closing), 'no_format_name': depreciation_closing},
                         # Gross
                        {'name': self.format_value(asset_gross), 'no_format_name': asset_gross},  # Gross
                    ],
                    'unfoldable': False,
                    'unfolded': False,
                    'caret_options': 'account.asset.line',
                    'group_id': al['asset_group_id'] or 0,
                    'group_name': al['asset_group_name'] or 'No Group Assigned',
                    'account_id': al['account_id']
                }
                if len(name) >= MAX_NAME_LENGTH:
                    line.update({'title_hover': name})
                lines.append(line)
        lines.append({
            'id': 'total',
            'level': 0,
            'name': _('Total'),
            'columns': [
                # Assets
                {'name': ''},
                {'name': self.format_value(total[0])},
                {'name': self.format_value(total[1])},
                {'name': self.format_value(total[2])},
                {'name': self.format_value(total[3])},
                {'name': ''},
                {'name': self.format_value(total[4])},# Assets
                # Cost
                {'name': self.format_value(total[5])},
                {'name': self.format_value(total[6])},
                {'name': self.format_value(total[7])},
                {'name': self.format_value(total[8])},# Cost
                # Depreciation
                {'name': self.format_value(total[9])},
                {'name': self.format_value(total[10])},
                {'name': self.format_value(total[11])},
                {'name': self.format_value(total[12])}, # Depreciation
                # # Gross
                {'name': self.format_value(total[13])},# Gross
            ],
            'unfoldable': False,
            'unfolded': False,
        })
        return lines

    @api.model
    def _create_hierarchy(self, lines, options):
        """Compute the hierarchy based on account groups when the option is activated.

        The option is available only when there are account.group for the company.
        It should be called when before returning the lines to the client/templater.
        The lines are the result of _get_lines(). If there is a hierarchy, it is left
        untouched, only the lines related to an account.account are put in a hierarchy
        according to the account.group's and their prefixes.
        """
        unfold_all = self.env.context.get('print_mode') and len(options.get('unfolded_lines')) == 0 or options.get('unfold_all')

        def add_to_hierarchy(lines, key, level, parent_id, hierarchy):
            val_dict = hierarchy[key]
            unfolded = val_dict['id'] in options.get('unfolded_lines') or unfold_all
            # add the group totals
            lines.append({
                'id': val_dict['id'],
                'name': val_dict['name'],
                'title_hover': val_dict['name'],
                'unfoldable': True,
                'unfolded': unfolded,
                'level': level,
                'parent_id': parent_id,
                'columns': [{'name': self.format_value(c) if isinstance(c, (int, float)) else c, 'no_format_name': c} for c in val_dict['totals']],
                'name_class': 'o_account_report_name_ellipsis top-vertical-align'
            })
            if not self._context.get('print_mode') or unfolded:
                # add every direct child group recursively
                for child in sorted(val_dict['children_codes']):
                    add_to_hierarchy(lines, child, level + 1, val_dict['id'], hierarchy)
                # add all the lines that are in this group but not in one of this group's children groups
                for l in val_dict['lines']:
                    l['level'] = level + 1
                    l['parent_id'] = val_dict['id']
                lines.extend(val_dict['lines'])

        def compute_hierarchy(lines, level, parent_id):
            # put every line in each of its parents (from less global to more global) and compute the totals
            hierarchy = defaultdict(lambda: {'totals': [None] * len(lines[0]['columns']), 'lines': [], 'children_codes': set(), 'name': '', 'parent_id': None, 'id': ''})
            for line in lines:
                account = self.env['account.account'].browse(line.get('account_id', self._get_caret_option_target_id(line.get('id'))))
                codes = self.get_account_codes(account)  # id, name
                for code in codes:
                    hierarchy[code[0]]['id'] = 'hierarchy_' + str(code[0])
                    hierarchy[code[0]]['name'] = code[1]
                    for i, column in enumerate(line['columns']):
                        if 'no_format_name' in column:
                            no_format = column['no_format_name']
                        elif 'no_format' in column:
                            no_format = column['no_format']
                        else:
                            no_format = None
                        if isinstance(no_format, (int, float)):
                            if hierarchy[code[0]]['totals'][i] is None:
                                hierarchy[code[0]]['totals'][i] = no_format
                            else:
                                hierarchy[code[0]]['totals'][i] += no_format
                for code, child in zip(codes[:-1], codes[1:]):
                    hierarchy[code[0]]['children_codes'].add(child[0])
                    hierarchy[child[0]]['parent_id'] = hierarchy[code[0]]['id']
                hierarchy[codes[-1][0]]['lines'] += [line]
            # compute the tree-like structure by starting at the roots (being groups without parents)
            hierarchy_lines = []
            for root in [k for k, v in hierarchy.items() if not v['parent_id']]:
                add_to_hierarchy(hierarchy_lines, root, level, parent_id, hierarchy)
            return hierarchy_lines

        def compute_hierarchy_group(lines, level, parent_id):
            # put every line in each of its parents (from less global to more global) and compute the totals
            hierarchy = defaultdict(lambda: {'totals': [None] * len(lines[0]['columns']), 'lines': [], 'children_codes': set(), 'name': '', 'parent_id': None, 'id': ''})
            for line in lines:
                codes = [(line['group_id'], line['group_name'])]
                for code in codes:
                    hierarchy[code[0]]['id'] = 'hierarchy_' + str(code[0])
                    hierarchy[code[0]]['name'] = code[1]
                    for i, column in enumerate(line['columns']):
                        if 'no_format_name' in column:
                            no_format = column['no_format_name']
                        elif 'no_format' in column:
                            no_format = column['no_format']
                        else:
                            no_format = None
                        if isinstance(no_format, (int, float)):
                            if hierarchy[code[0]]['totals'][i] is None:
                                hierarchy[code[0]]['totals'][i] = no_format
                            else:
                                hierarchy[code[0]]['totals'][i] += no_format
                for code, child in zip(codes[:-1], codes[1:]):
                    hierarchy[code[0]]['children_codes'].add(child[0])
                    hierarchy[child[0]]['parent_id'] = hierarchy[code[0]]['id']
                hierarchy[codes[-1][0]]['lines'] += [line]
            # compute the tree-like structure by starting at the roots (being groups without parents)
            hierarchy_lines = []
            for root in [k for k, v in hierarchy.items() if not v['parent_id']]:
                add_to_hierarchy(hierarchy_lines, root, level, parent_id, hierarchy)
            return hierarchy_lines

        new_lines = []
        account_lines = []
        current_level = 0
        parent_id = 'root'
        for line in lines:
            if not (line.get('caret_options') == 'account.account' or line.get('account_id')):
                # make the hierarchy with the lines we gathered, append it to the new lines and restart the gathering
                if account_lines:
                    new_lines.extend(compute_hierarchy_group(account_lines, current_level + 2, parent_id))
                account_lines = []
                new_lines.append(line)
                current_level = line['level']
                parent_id = line['id']
            else:
                # gather all the lines we can create a hierarchy on
                account_lines.append(line)
        # do it one last time for the gathered lines remaining  
        if account_lines:
            new_lines.extend(compute_hierarchy(account_lines, current_level + 2, parent_id))        
        final_lines = []
        # _logger.error("*********************** lines : %s", new_lines)
        for new_line in new_lines:
            if new_line.get('parent_id') == 'root':
                final_lines.append(new_line)
                to_precess_lines = []
                for new_line_dum in new_lines:
                    if new_line_dum.get('parent_id') == new_line.get('id'):
                        to_precess_lines.append(new_line_dum)
                # _logger.error("***********************lines : %s - %s", new_line.get('id'), len(to_precess_lines))
                if to_precess_lines:
                    new_lines_dum = []
                    account_lines_dum = []
                    current_level_dum = 0
                    parent_id_dum = new_line.get('id')
                    for to_precess_line in to_precess_lines:
                        if not (to_precess_line.get('caret_options') == 'account.account' or to_precess_line.get('account_id')):
                            # make the hierarchy with the lines we gathered, append it to the new lines and restart the gathering
                            if account_lines_dum:
                                new_lines_dum.extend(compute_hierarchy(account_lines_dum, current_level_dum + 1, parent_id_dum))
                            account_lines_dum = []
                            new_lines_dum.append(to_precess_line)
                            current_level_dum = to_precess_line['level']
                            parent_id_dum = to_precess_line['id']
                        else:
                            # gather all the lines we can create a hierarchy on
                            account_lines_dum.append(to_precess_line)
                    # do it one last time for the gathered lines remaining  
                    if account_lines_dum:
                        new_lines_dum.extend(compute_hierarchy(account_lines_dum, current_level_dum + 1, parent_id_dum))
                    for new_line_dum in new_lines_dum:
                        final_lines.append(new_line_dum)
            if new_line.get('id') == 'total':
                final_lines.append(new_line)
        # _logger.error("***********************New lines : %s", final_lines)
        return final_lines

    def _get_assets_lines(self, options):
        "Get the data from the database"

        self.env['account.move.line'].check_access_rights('read')
        self.env['account.asset'].check_access_rights('read')

        where_account_move = " AND state != 'cancel'"
        if not options.get('all_entries'):
            where_account_move = " AND state = 'posted'"

        sql = """
                -- remove all the moves that have been reversed from the search
                CREATE TEMPORARY TABLE IF NOT EXISTS temp_account_move () INHERITS (account_move) ON COMMIT DROP;
                INSERT INTO temp_account_move SELECT move.*
                FROM ONLY account_move move
                LEFT JOIN ONLY account_move reversal ON reversal.reversed_entry_id = move.id
                WHERE reversal.id IS NULL AND move.asset_id IS NOT NULL AND move.company_id in %(company_ids)s;

                SELECT asset.id as asset_id,
                       asset.parent_id as parent_id,
                       asset.name as asset_name,
                       asset.tax_original_value as asset_original_value,
                       asset.currency_id as asset_currency_id,
                       COALESCE(asset.tax_first_depreciation_date) as asset_date,
                       asset.already_depreciated_amount_import as import_depreciated,
                       asset.disposal_date as asset_disposal_date,
                       asset.tax_acquisition_date as asset_acquisition_date,
                       asset.tax_x_value_addition as asset_x_value_addition,
                       asset.value_addition as asset_value_addition,
                       asset.tax_purch_price as asset_tax_purch_price,
                       asset.value_revaluation as asset_value_revaluation,
                       asset.value_residual as asset_value_residual,
                       asset.tax_method as asset_method,
                       (
                           account_move_count.count
                           + COALESCE(0)
                           - CASE WHEN asset.tax_prorata THEN 1 ELSE 0 END
                       ) as asset_method_number,
                       asset.tax_method_period as asset_method_period,
                       asset.tax_method_progress_factor as asset_method_progress_factor,
                       asset.tax_depreciation_percentage as asset_depreciation_percentage,
                       asset.state as asset_state,
                       account.code as account_code,
                       account.name as account_name,
                       account.id as account_id,
                       account.company_id as company_id,
                       asset_group.name as asset_group_name,
                       asset_group.id as asset_group_id,
                       COALESCE(first_move.asset_depreciated_value, move_before.asset_depreciated_value, 0.0) as depreciated_start,
                       COALESCE(first_move.asset_remaining_value, move_before.asset_remaining_value, 0.0) as remaining_start,
                       COALESCE(last_move.asset_depreciated_value, move_before.asset_depreciated_value, 0.0) as depreciated_end,
                       COALESCE(last_move.asset_remaining_value, move_before.asset_remaining_value, 0.0) as remaining_end,
                       COALESCE(first_move.amount_total, 0.0) as depreciation,
                       COALESCE(first_move.id, move_before.id) as first_move_id,
                       COALESCE(last_move.id, move_before.id) as last_move_id
                FROM account_asset as asset
                LEFT JOIN account_account as account ON asset.account_asset_id = account.id
                LEFT JOIN account_asset_group as asset_group ON asset.group_id = asset_group.id
                LEFT JOIN (
                    SELECT
                        COUNT(*) as count,
                        asset_id
                    FROM temp_account_move
                    WHERE asset_value_change != 't'
                    GROUP BY asset_id
                ) account_move_count ON asset.id = account_move_count.asset_id

                LEFT OUTER JOIN (
                    SELECT DISTINCT ON (asset_id)
                        id,
                        asset_depreciated_value,
                        asset_remaining_value,
                        amount_total,
                        asset_id
                    FROM temp_account_move m
                    WHERE date >= %(date_from)s AND date <= %(date_to)s {where_account_move}
                    ORDER BY asset_id, date, id DESC
                ) first_move ON first_move.asset_id = asset.id

                LEFT OUTER JOIN (
                    SELECT DISTINCT ON (asset_id)
                        id,
                        asset_depreciated_value,
                        asset_remaining_value,
                        amount_total,
                        asset_id
                    FROM temp_account_move m
                    WHERE date >= %(date_from)s AND date <= %(date_to)s {where_account_move}
                    ORDER BY asset_id, date DESC, id DESC
                ) last_move ON last_move.asset_id = asset.id

                LEFT OUTER JOIN (
                    SELECT DISTINCT ON (asset_id)
                        id,
                        asset_depreciated_value,
                        asset_remaining_value,
                        amount_total,
                        asset_id
                    FROM temp_account_move m
                    WHERE date <= %(date_from)s {where_account_move}
                    ORDER BY asset_id, date DESC, id DESC
                ) move_before ON move_before.asset_id = asset.id

                WHERE asset.company_id in %(company_ids)s
                AND asset.tax_acquisition_date <= %(date_to)s
                AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
                AND asset.state not in ('model', 'draft')
                AND asset.asset_type = 'purchase'
                AND asset.active = 't'

                ORDER BY account.code, asset.tax_acquisition_date;
            """.format(where_account_move=where_account_move)

        date_to = options['date']['date_to']
        date_from = options['date']['date_from']
        if options.get('multi_company', False):
            company_ids = tuple(self.env.companies.ids)
        else:
            company_ids = tuple(self.env.company.ids)

        self.flush()
        self.env.cr.execute(sql, {'date_to': date_to, 'date_from': date_from, 'company_ids': company_ids})
        results = self.env.cr.dictfetchall()
        self.env.cr.execute("DROP TABLE temp_account_move")  # Because tests are run in the same transaction, we need to clean here the SQL INHERITS

        addition_sql = """ 
            SELECT asset_id, sum(tax_value_amount)
            FROM asset_value_addition 
            WHERE company_id in %(company_ids)s
            AND date >= %(date_from)s
            AND date <= %(date_to)s
            GROUP BY asset_id
        """
        self.flush()
        self.env.cr.execute(addition_sql, {'date_to': date_to, 'date_from': date_from, 'company_ids': company_ids})
        addition_results = self.env.cr.dictfetchall()
        for result in results:
            result['asset_x_value_addition_current'] = 0.00
            for addition_result in addition_results:
                if result['asset_id'] == addition_result['asset_id']:
                    result['asset_x_value_addition_current'] = addition_result['sum']
                    break

        addition_before_sql = """ 
            SELECT asset_id, sum(tax_value_amount)
            FROM asset_value_addition 
            WHERE company_id in %(company_ids)s
            AND date < %(date_from)s
            GROUP BY asset_id
        """
        self.flush()
        self.env.cr.execute(addition_before_sql, {'date_from': date_from, 'company_ids': company_ids})
        addition_results = self.env.cr.dictfetchall()
        for result in results:
            result['asset_x_value_addition_before'] = 0.00
            for addition_result in addition_results:
                if result['asset_id'] == addition_result['asset_id']:
                    result['asset_x_value_addition_before'] = addition_result['sum']
                    break
        
        total_depreciation_sql = """ 
            SELECT asset_id, sum(depreciation)
            FROM account_asset_tax 
            WHERE company_id in %(company_ids)s
            AND date <= %(date_today)s

            GROUP BY asset_id
        """
        self.flush()
        self.env.cr.execute(total_depreciation_sql, {'date_today': fields.Date.today(), 'company_ids': company_ids})


        total_depreciation_results = self.env.cr.dictfetchall()
        for result in results:
            result['asset_total_depreciation'] = 0.00
            for total_depreciation_result in total_depreciation_results:
                if result['asset_id'] == total_depreciation_result['asset_id']:
                    result['asset_total_depreciation'] = total_depreciation_result['sum']
                    break
        
        total_depreciation_before_sql = """ 
            SELECT asset_id, sum(depreciation)
            FROM account_asset_tax 
            WHERE company_id in %(company_ids)s
            AND date < %(date_from)s
            AND date <= %(date_today)s
            GROUP BY asset_id
        """
        self.flush()
        self.env.cr.execute(total_depreciation_before_sql, {'date_from': date_from, 'date_today': fields.Date.today(), 'company_ids': company_ids})
        total_depreciation_before_results = self.env.cr.dictfetchall()
        for result in results:
            result['asset_total_depreciation_before'] = 0.00
            for total_depreciation_before_result in total_depreciation_before_results:
                if result['asset_id'] == total_depreciation_before_result['asset_id']:
                    result['asset_total_depreciation_before'] = total_depreciation_before_result['sum']
                    break
        
        total_depreciation_current_sql = """ 
            SELECT asset_id, sum(depreciation)
            FROM account_asset_tax 
            WHERE company_id in %(company_ids)s
            AND date >= %(date_from)s
            AND date <= %(date_to)s
            AND date <= %(date_today)s

            GROUP BY asset_id
        """
        self.flush()
        self.env.cr.execute(total_depreciation_current_sql, {'date_to': date_to, 'date_from': date_from, 'date_today': fields.Date.today(), 'company_ids': company_ids})


        total_depreciation_current_results = self.env.cr.dictfetchall()
        for result in results:
            result['asset_total_depreciation_current'] = 0.00
            for total_depreciation_current_result in total_depreciation_current_results:
                if result['asset_id'] == total_depreciation_current_result['asset_id']:
                    result['asset_total_depreciation_current'] = total_depreciation_current_result['sum']
                    break
                
        return results

    def open_asset(self, options, params=None):
        active_id = int(params.get('id').split('_')[-1])
        line = self.env['account.asset'].browse(active_id)
        return {
            'name': line.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'view_mode': 'form',
            'view_id': False,
            'views': [(self.env.ref('account_asset.view_account_asset_form').id, 'form')],
            'res_id': line.id,
        }
