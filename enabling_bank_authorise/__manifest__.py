# -*- coding: utf-8 -*-
{
    'name': "Bank Authorise - Enabling",

    'summary': "Bank Authorise - Enabling",

    'description': """
        This module has a feature to define list of users can authorise bank accounts.
    """,

    'author': "Enabling Ltd",
    'website': "www.enabling.co.nz",

    'category': 'Accounting/Accounting',
    #'version': '18.01.01',

    # any module necessary for this one to work correctly
    'depends': ['electronic_fund_transfer'],

    # always loaded
    'data': [
        'data/ir_module_category_data.xml',
        'views/res_company_views.xml',
        'views/res_bank_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
