# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    solar_quick_price = fields.Float(
        string='Costo por Watt Rápido por Defecto',
        config_parameter='cotizador_solar.default_quick_price',
        default=0.75
    )
    solar_quick_min_price = fields.Float(
        string='Precio Mínimo Rápido por Defecto',
        config_parameter='cotizador_solar.default_quick_min_price',
        default=3500.0
    )
