# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Enabling Partner History',
    'version': '1.2',
    'category': '',
    'sequence': 1,
    'summary': 'Partner History',
    'author': 'Enabling Limited',
    'description': "Used for displaying Partner History",
    'website': 'https://www.enabling.co.nz',
    'images': [
        
    ],
    'depends': [
        'base',
        'sale'
    ],
    'data': [
      'security/ir.model.access.csv',
      'views/enabling_partner_history.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
