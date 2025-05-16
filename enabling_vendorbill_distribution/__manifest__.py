# -*- coding: utf-8 -*-
{
    'name': "Vendor Bill distribution - Enabling",
    'summary': "Vendor Bill distribution - Enabling",
    'description': """
        Vendor Bill distribution - Enabling
    """,
    'author': "Enabling Ltd",
    'website': "www.enabling.co.nz",
    'category': 'Accounting/Accounting',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',

    'depends': [
        'account',
        'account_accountant',
    ],

    'data': [
        'security/ir.model.access.csv',
        'wizard/distribute_expense_views.xml',
        'views/account_move_views.xml',
        'views/account_reconcile_model_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'enabling_vendorbill_distribution/static/src/xml/account_reconciliation.xml',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}
