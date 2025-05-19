# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Enabling Accounting Date',
    'version': '1.1',
    'summary': 'Enabling Accounting Date',
    'sequence': 10,
    'description': """
Accounting Date in Customer Invoice & Credit Notes
==================================================
This module makes the Accounting Date field visible in Customer Invoice & Credit Notes forms. 
    """,
    'category': 'Accounting/Accounting',
    'website': 'https://www.enabling.co.nz',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
