# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SolarConfig(models.Model):
    _name = 'solar.config'
    _description = 'Configuración de Referencia Solar'

    quick_price = fields.Float(string='Costo por Watt Rápido por Defecto', default=0.75, required=True)
    quick_min_price = fields.Float(string='Precio Mínimo Rápido por Defecto', default=3500.0, required=True)
    min_panel_count = fields.Integer(string='Cantidad de paneles mínimos', default=8)
    default_panel_watts = fields.Integer(string='Tamaño de panel por defecto', default=590)
    product_id = fields.Many2one(
        'product.product', 
        string='Producto', 
        help="Seleccione el producto del catálogo que se agregará automáticamente a la línea de venta al generar la cotización."
    )
    description_template = fields.Text(
        string='Plantilla de Descripción', 
        help="Plantilla dinámica para la descripción. Utilice la etiqueta [pppp] para inyectar automáticamente el Tamaño de la planta (kWp) y [gggg] para la Generación mensual (kWh/m)."
    )

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
