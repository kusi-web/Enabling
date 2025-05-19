# -*- coding: utf-8 -*-

{
    'name': 'Electronic Fund Transfer',
    'version': '2020.04.29',
    'author': 'Enabling NZ (www.enabling.co.nz)',
    'summary': """Electronic Fund Transfer Processing.""",
    'description': """Electronic Fund Transfer Processing.""",
    "category": "Accounting",
    'depends': ['account', 'account_accountant', 'payment'],
    'data': [
        'views/account_eft.xml',
        'views/report_invoice.xml',

        'wizards/eft_export_wizard.xml',
        'wizards/account_payment_register.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
}
