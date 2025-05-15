# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project - Enabling',
    'version': '1.1',
    'website': 'https://www.odoo.com/page/project-management',
    'category': 'Services/Project',
    'sequence': 45,
    'summary': 'Organize and plan your projects - Extended',
    'depends': [
        'project',
        'account',
        'account_accountant'
    ],
    'description': "",
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/project_views.xml',
        'views/analytic_account_views.xml',
        'views/account_account_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
