{
    'name': 'Inmobiliaria Core',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Gestión extendida de propiedades, ofertas y clientes para inmobiliaria',
    'description': """
Módulo base para inmobiliaria que extiende real_estate nativo de Odoo.
Añade campos específicos del mercado argentino/latam, workflows comerciales
y integración con website público.
    """,
    'author': 'Tu Inmobiliaria',
    'website': 'https://tu-inmobiliaria.com',
    'depends': [
        'real_estate',
        'website',
        'crm',
        'account',
        'sign',
        'documents',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/property_views.xml',
        'views/property_menu.xml',
        'views/wizard_views.xml',
        'data/demo_data.xml',
        'data/email_templates.xml',
    ],
    'demo': ['data/demo_data.xml'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}