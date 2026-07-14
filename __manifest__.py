{
    'name': "Cotizador de Solución Solar",
    'summary': """
        Cotizador y dimensionador de soluciones solares para clientes integrado con Contactos y Ventas.
    """,
    'description': """
        Módulo para el dimensionamiento técnico y financiero de sistemas solares fotovoltaicos.
        Permite:
        - Registrar y analizar los consumos de 12 meses de un cliente de Odoo.
        - Calcular la potencia pico, radiación HSP, cantidad de paneles y precios estimados.
        - Generar un Pedido de Venta en Odoo adjuntando automáticamente la propuesta técnica en PDF.
    """,
    'author': "Brooks Gonzalez",
    'company': "MBAConsultings",
    'maintainer': 'MBAConsultings',
    'website': "https://mbaconsultings.com",
    'support': "ventas@mbaconsultings.com",
    'license': "AGPL-3",
    'category': 'Sales',
    'version': '18.0.1.0.3',
    'depends': ['base', 'sale', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/solar_quote_views.xml',
        'reports/solar_quote_report.xml',
        'reports/solar_quote_report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cotizador-solar/static/src/css/cotizador_solar.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
