# -*- coding: utf-8 -*-
{
    'name': "Transport",

    'summary': """
	    Transport Management System
        """,

    'description': """
        Transport Management System
    """,

    'author': "toolter",
    'website': "http://www.toolter.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Toolter',
    'version': '9.0c-20171020',

    # any module necessary for this one to work correctly
    'depends': ['hr_expense','hr_payroll','hr_holidays','product','base_geoengine','fleet'],

    'external_dependencies': {
        'python': [
#            'sodapy',
#            'num2words',
        ],
    },
    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/menu_payroll.xml',
        'views/menu_transport.xml',
        'views/account_invoice.xml',
        'views/transport_agence.xml',
        'views/transport_carburation.xml',
        'views/transport_chauffeur.xml', 
        'views/transport_colis.xml',     
        'views/transport_endroit.xml',
        'views/transport_feuilleroute.xml',
        'views/hr_employee.xml',
        'views/transport_motoboy.xml',
        'views/transport_passager.xml',
        'views/transport_peage.xml',  
        'views/transport_piece.xml',
        'views/transport_route.xml',  
        'views/transport_vehicule.xml',  
        'views/transport_voyage.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable' : True,
    'application' : True,
}