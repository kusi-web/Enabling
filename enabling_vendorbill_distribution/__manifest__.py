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
    'version': '14',

    # any module necessary for this one to work correctly
    'depends': ['account', 'account_accountant'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/distribute_expense_views.xml',
        'views/account_move_views.xml',
        'views/account_reconcile_model_views.xml'
    ],
    'demo': [],
    'qweb': ["static/src/xml/account_reconciliation.xml"],
    'installable': True,
    'application': True,
    'auto_install': False,
}
