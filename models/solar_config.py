# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SolarConfig(models.Model):
    _name = 'solar.config'
    _description = 'Configuración de Referencia Solar'

    quick_price = fields.Float(string='Costo por Watt Rápido por Defecto', default=0.75, required=True)
    quick_min_price = fields.Float(string='Precio Mínimo Rápido por Defecto', default=3500.0, required=True)
    product_id = fields.Many2one('product.product', string='Producto')
    description_template = fields.Text(string='Plantilla de Descripción')

    @api.constrains('description_template')
    def _check_description_template(self):
        for record in self:
            text = record.description_template or ''
            if '[pppp]' not in text or '[gggg]' not in text:
                raise ValidationError("La plantilla de descripción debe contener las etiquetas '[pppp]' y '[gggg]'.")

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
