{
    'name': "AutoFix",
    'author': "Abdo Mohamed",
    'category': "Services",
    'version': '17.0.0.1.0',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/car_views.xml',
        'views/service_reception_views.xml',
        'views/work_order_views.xml',
        'views/petty_cash_views.xml',
        'views/menus.xml',
    ],
    'application': True,
}
