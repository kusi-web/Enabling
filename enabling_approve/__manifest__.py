# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Approve - Enabling',
    'version': '1.1',
    'website': '',
    'category': 'Approvals',
    'sequence': 45,
    'summary': 'Approve Vendor Bills',
    'depends': [
        'base',
        'account',
        'enabling_project',
        # 'nwo_studio_fields',
        'enabling_partner_history',
    ],
    'description': "",
    'data': [
        'security/ir.model.access.csv',
        'wizard/bill_reject_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/res_company_views.xml',
        # 'views/res_partner_views.xml',
        'template/email_templates.xml',
        'wizard/duplicate_vendor_bill_alert.xml', #sushma
        'views/account_config_view.xml',  #sushma
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
