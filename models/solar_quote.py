# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SolarQuote(models.Model):
    _name = 'solar.quote'
    _description = 'Cotización Solar'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, index=True, default=lambda self: _('Nuevo'))
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True)
    ubicacion = fields.Char(string='Ubicación', tracking=True)
    medidor = fields.Char(string='Medidor No.', tracking=True)
    nac = fields.Char(string='NAC No.', tracking=True)

    mode = fields.Selection([
        ('quick', 'Modo Rápido'),
        ('advanced', 'Modo Avanzado')
    ], string='Modo de Cálculo', default='quick', required=True, tracking=True)

    start_month = fields.Selection([
        ('0', 'Enero'), ('1', 'Febrero'), ('2', 'Marzo'), ('3', 'Abril'),
        ('4', 'Mayo'), ('5', 'Junio'), ('6', 'Julio'), ('7', 'Agosto'),
        ('8', 'Septiembre'), ('9', 'Octubre'), ('10', 'Noviembre'), ('11', 'Diciembre')
    ], string='Mes Inicio', default=lambda self: str(fields.Date.today().month - 1), required=True)
    start_year = fields.Integer(string='Año Inicio', default=lambda self: fields.Date.today().year, required=True)

    # Consumos mensuales
    consumption_m1 = fields.Integer(string='Mes 1', default=0)
    consumption_m2 = fields.Integer(string='Mes 2', default=0)
    consumption_m3 = fields.Integer(string='Mes 3', default=0)
    consumption_m4 = fields.Integer(string='Mes 4', default=0)
    consumption_m5 = fields.Integer(string='Mes 5', default=0)
    consumption_m6 = fields.Integer(string='Mes 6', default=0)
    consumption_m7 = fields.Integer(string='Mes 7', default=0)
    consumption_m8 = fields.Integer(string='Mes 8', default=0)
    consumption_m9 = fields.Integer(string='Mes 9', default=0)
    consumption_m10 = fields.Integer(string='Mes 10', default=0)
    consumption_m11 = fields.Integer(string='Mes 11', default=0)
    consumption_m12 = fields.Integer(string='Mes 12', default=0)

    def _default_quick_price(self):
        return self.env['solar.config'].get_config().quick_price

    def _default_quick_min_price(self):
        return self.env['solar.config'].get_config().quick_min_price

    # Configuración Rápida
    quick_hsp = fields.Float(string='Radiación (HSP) Rápida', default=3.5)
    quick_price = fields.Float(string='Costo por Watt Rápido', default=_default_quick_price)
    quick_min_price = fields.Float(string='Precio Mínimo Rápido', default=_default_quick_min_price)
    quick_panel_watts = fields.Float(string='Watts del Panel Rápido', default=590.0)
    quick_min_panels = fields.Integer(string='Cant. Mínima de Paneles', default=8)

    # Configuración Técnica / Avanzada
    advanced_hsp = fields.Float(string='Radiación (HSP) Avanzada', default=3.5)
    advanced_efficiency = fields.Float(string='Eficiencia (%)', default=100.0)
    advanced_panel_watts = fields.Float(string='Watts del Panel Avanzado', default=600.0)
    advanced_panel_count = fields.Integer(string='Cantidad de Módulos', default=8)
    pricing_mode = fields.Selection([
        ('watt', '$/Watt'),
        ('total', 'Precio Total')
    ], string='Modo de Costo', default='watt')
    pricing_value = fields.Float(string='Valor de Costo', default=0.75)
    advanced_min_price = fields.Float(string='Precio Mínimo Avanzado', default=3500.0)

    # Resultados e Inteligencia de Consumo (Calculados)
    total_yearly_consumption = fields.Integer(string='Consumo Total (Año)', compute='_compute_consumption_stats', store=True)
    avg_monthly_consumption = fields.Integer(string='Consumo Mensual Promedio', compute='_compute_consumption_stats', store=True)
    avg_daily_consumption = fields.Integer(string='Consumo Diario Promedio', compute='_compute_consumption_stats', store=True)
    peak_consumption = fields.Integer(string='Consumo Pico (Max)', compute='_compute_consumption_stats', store=True)
    min_consumption = fields.Integer(string='Consumo Mínimo (Min)', compute='_compute_consumption_stats', store=True)

    # Resultados del Dimensionamiento
    plant_size = fields.Float(string='Tamaño de Planta (kWp)', compute='_compute_solar_calculations', store=True)
    panel_count = fields.Integer(string='Total de Módulos (Paneles)', compute='_compute_solar_calculations', store=True)
    investment = fields.Float(string='Inversión Estimada', compute='_compute_solar_calculations', store=True)
    cost_per_watt = fields.Float(string='Costo por Watt ($/W)', compute='_compute_solar_calculations', store=True)
    coverage = fields.Float(string='Cobertura del Sistema (%)', compute='_compute_solar_calculations', store=True)
    
    is_min_price_applied = fields.Boolean(string='Precio Mínimo Aplicado', compute='_compute_solar_calculations', store=True)
    is_min_plant_applied = fields.Boolean(string='Planta Mínima Aplicada', compute='_compute_solar_calculations', store=True)

    generation_daily = fields.Float(string='Generación Diaria (kWh)', compute='_compute_solar_calculations', store=True)
    generation_monthly = fields.Float(string='Generación Mensual (kWh)', compute='_compute_solar_calculations', store=True)
    generation_yearly = fields.Float(string='Generación Anual (kWh)', compute='_compute_solar_calculations', store=True)

    # Campo técnico para relacionar la cotización comercial creada
    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta Generado', readonly=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('solar.quote') or _('Nuevo')
        return super().create(vals_list)

    @api.depends(
        'consumption_m1', 'consumption_m2', 'consumption_m3', 'consumption_m4',
        'consumption_m5', 'consumption_m6', 'consumption_m7', 'consumption_m8',
        'consumption_m9', 'consumption_m10', 'consumption_m11', 'consumption_m12'
    )
    def _compute_consumption_stats(self):
        for rec in self:
            consumptions = [
                rec.consumption_m1, rec.consumption_m2, rec.consumption_m3, rec.consumption_m4,
                rec.consumption_m5, rec.consumption_m6, rec.consumption_m7, rec.consumption_m8,
                rec.consumption_m9, rec.consumption_m10, rec.consumption_m11, rec.consumption_m12
            ]
            total = sum(consumptions)
            rec.total_yearly_consumption = total
            rec.avg_monthly_consumption = int(round(total / 12.0))
            rec.avg_daily_consumption = int(round((total / 12.0) / 30.0))
            rec.peak_consumption = max(consumptions) if consumptions else 0
            rec.min_consumption = min(consumptions) if consumptions else 0

    @api.depends(
        'mode', 'total_yearly_consumption', 'avg_daily_consumption', 'avg_monthly_consumption',
        'quick_hsp', 'quick_price', 'quick_min_price', 'quick_panel_watts', 'quick_min_panels',
        'advanced_hsp', 'advanced_efficiency', 'advanced_panel_watts', 'advanced_panel_count',
        'pricing_mode', 'pricing_value', 'advanced_min_price'
    )
    def _compute_solar_calculations(self):
        for rec in self:
            if rec.total_yearly_consumption <= 0:
                rec.plant_size = 0.0
                rec.panel_count = 0
                rec.investment = 0.0
                rec.cost_per_watt = 0.0
                rec.coverage = 0.0
                rec.is_min_price_applied = False
                rec.is_min_plant_applied = False
                rec.generation_daily = 0.0
                rec.generation_monthly = 0.0
                rec.generation_yearly = 0.0
                continue

            if rec.mode == 'quick':
                hsp = rec.quick_hsp or 3.5
                price_per_watt = rec.quick_price or rec._default_quick_price()
                min_price = rec.quick_min_price or rec._default_quick_min_price()
                p_watts = rec.quick_panel_watts or 590.0
                min_panels = rec.quick_min_panels or 8
                min_plant_size = (min_panels * p_watts) / 1000.0

                theoretical_plant_size = rec.avg_daily_consumption / hsp
                theoretical_investment = theoretical_plant_size * 1000.0 * price_per_watt

                if theoretical_investment < min_price:
                    rec.investment = min_price
                    rec.is_min_price_applied = True
                    config = self.env['solar.config'].get_config()
                    rec.plant_size = (config.min_panel_count * config.default_panel_watts) / 1000.0
                    rec.is_min_plant_applied = True
                    rec.generation_monthly = rec.plant_size * 3.5 * 30.0
                    rec.generation_daily = rec.generation_monthly / 30.0
                else:
                    rec.investment = theoretical_investment
                    rec.is_min_price_applied = False
                    rec.plant_size = theoretical_plant_size
                    rec.is_min_plant_applied = False
                    rec.generation_daily = rec.plant_size * hsp
                    rec.generation_monthly = rec.generation_daily * 30.0

                rec.generation_yearly = rec.generation_monthly * 12.0
                rec.panel_count = int(abs((rec.plant_size * 1000.0) / p_watts))
                
                if rec.is_min_price_applied:
                    rec.cost_per_watt = rec.investment / (rec.plant_size * 1000.0) if rec.plant_size > 0 else 0.0
                else:
                    rec.cost_per_watt = price_per_watt

            else:  # advanced mode
                hsp = rec.advanced_hsp or 3.5
                eff = (rec.advanced_efficiency or 100.0) / 100.0
                p_watts = rec.advanced_panel_watts or 600.0
                p_count = rec.advanced_panel_count or 0

                rec.plant_size = (p_count * p_watts) / 1000.0
                rec.panel_count = p_count

                rec.generation_daily = rec.plant_size * hsp * eff
                rec.generation_monthly = rec.generation_daily * (365.0 / 12.0)
                rec.generation_yearly = rec.generation_daily * 365.0

                min_price = rec.advanced_min_price
                val = rec.pricing_value

                if rec.pricing_mode == 'watt':
                    theoretical_investment = rec.plant_size * 1000.0 * val
                else:
                    theoretical_investment = val

                if theoretical_investment < min_price:
                    rec.investment = min_price
                    rec.is_min_price_applied = True
                else:
                    rec.investment = theoretical_investment
                    rec.is_min_price_applied = False

                if rec.plant_size > 0:
                    rec.cost_per_watt = rec.investment / (rec.plant_size * 1000.0)
                else:
                    rec.cost_per_watt = 0.0
                rec.is_min_plant_applied = False

            rec.coverage = (rec.generation_yearly / rec.total_yearly_consumption) if rec.total_yearly_consumption > 0 else 0.0

    def action_auto_size_advanced(self):
        """Ajusta automáticamente el número de paneles en Modo Avanzado para cubrir el 100% del consumo."""
        self.ensure_one()
        if self.mode != 'advanced':
            return
        hsp = self.advanced_hsp or 3.5
        eff = (self.advanced_efficiency or 100.0) / 100.0
        p_watts = self.advanced_panel_watts or 600.0
        
        # Plant size in kWp needed to cover avg_daily_consumption
        needed_kwp = self.avg_daily_consumption / (hsp * eff)
        needed_watts = needed_kwp * 1000.0
        
        # Calculate panel count
        new_count = int(abs(needed_watts / p_watts))
        if new_count * p_watts < needed_watts:
            new_count += 1
        
        self.advanced_panel_count = new_count

    def action_generate_proposal(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Por favor, seleccione un cliente antes de generar la propuesta."))

        config = self.env['solar.config'].get_config()

        # Crear el presupuesto de venta
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
        })

        # Formatear a 2 decimales
        plant_size_str = f"{self.plant_size:.2f}"
        generation_monthly_str = f"{self.generation_monthly:.2f}"

        description = config.description_template or ''
        description = description.replace('[pppp]', plant_size_str)
        description = description.replace('[gggg]', generation_monthly_str)

        # Crear la línea del pedido de venta
        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': config.product_id.id,
            'name': description,
            'price_unit': round(self.investment, 2),
            'product_uom_qty': 1.0,
        })

        self.sale_order_id = sale_order.id

        # Renderizar el PDF de la propuesta en memoria
        report = self.env.ref('cotizador_solar.action_report_solar_proposal')
        pdf_content, content_type = report._render_qweb_pdf(self.ids)

        # Crear adjunto
        attachment = self.env['ir.attachment'].create({
            'name': f"Propuesta_Solar_{self.partner_id.name}_{fields.Date.today()}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'mimetype': 'application/pdf',
        })

        # Adjuntar al chatter del pedido de venta
        sale_order.message_post(
            body=f"Propuesta técnica y económica de solución solar adjuntada automáticamente desde el Cotizador Solar (Ref: {self.name}).",
            attachment_ids=[attachment.id]
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
