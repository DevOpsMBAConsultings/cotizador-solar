# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SolarConfig(models.Model):
    _name = 'solar.config'
    _description = 'Configuración de Referencia Solar'

    quick_price = fields.Float(string='Costo por Watt Rápido por Defecto', default=0.75, required=True)
    quick_min_price = fields.Float(string='Precio Mínimo Rápido por Defecto', default=3500.0, required=True)

    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    @api.model
    def action_open_config(self):
        config = self.get_config()
        return {
            'name': 'Configuración Cotizador Solar',
            'type': 'ir.actions.act_window',
            'res_model': 'solar.config',
            'view_mode': 'form',
            'res_id': config.id,
            'target': 'current',
        }
