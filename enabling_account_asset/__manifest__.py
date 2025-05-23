# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Assets Management - Enabling',
    'description': "",
    'category': 'Accounting/Accounting',
    'sequence': 32,
    'depends': ['account_asset'],    
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'wizard/asset_batch_process_views.xml',
        # 'wizard/asset_sell_views.xml',
        'views/account_asset_views.xml',
        'views/asset_value_addition_views.xml',
        'views/res_company_views.xml',
        'report/account_assets_tax_report_views.xml',
        'wizard/imp_asset_revaluation_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'enabling_account_asset/static/src/scss/account_asset.scss',
        ],
    },
    'demo': [],
    'license': 'OEEL-1',
    'auto_install': False,
}
