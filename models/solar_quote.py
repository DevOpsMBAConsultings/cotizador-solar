# -*- coding: utf-8 -*-
import base64
import json
import requests
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

    def _default_advanced_efficiency(self):
        return self.env['solar.config'].get_config().default_efficiency or 100.0

    # Configuración Rápida
    quick_hsp = fields.Float(string='Radiación (HSP) Rápida', default=3.5)
    quick_price = fields.Float(string='Costo por Watt Rápido', default=_default_quick_price)
    quick_min_price = fields.Float(string='Precio Mínimo Rápido', default=_default_quick_min_price)
    quick_panel_watts = fields.Float(string='Watts del Panel Rápido', default=590.0)
    quick_min_panels = fields.Integer(string='Cant. Mínima de Paneles', default=8)

    # Configuración Técnica / Avanzada
    advanced_hsp = fields.Float(string='Radiación (HSP) Avanzada', default=3.5)
    advanced_efficiency = fields.Float(string='Eficiencia (%)', default=_default_advanced_efficiency)
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
    avg_monthly_consumption = fields.Float(string='Consumo Mensual Promedio', compute='_compute_consumption_stats', store=True, digits=(16, 2))
    avg_daily_consumption = fields.Float(string='Consumo Diario Promedio', compute='_compute_consumption_stats', store=True, digits=(16, 4))
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

    # Integración Inteligencia Artificial
    invoice_file = fields.Binary(string='Factura Adjunta', attachment=True)
    invoice_file_name = fields.Char(string='Nombre del Archivo')

    # Campo técnico para relacionar la cotización comercial creada
    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta Generado', readonly=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('solar.quote') or _('Nuevo')
        records = super().create(vals_list)
        for rec in records:
            if rec.invoice_file:
                rec._attach_invoice_file_to_chatter()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'invoice_file' in vals and vals['invoice_file']:
            for rec in self:
                rec._attach_invoice_file_to_chatter()
        return res

    def _attach_invoice_file_to_chatter(self):
        for rec in self:
            if not rec.invoice_file:
                continue
            filename = rec.invoice_file_name or _("Factura_Electrica.pdf")
            existing = self.env['ir.attachment'].search([
                ('res_model', '=', 'solar.quote'),
                ('res_id', '=', rec.id),
                ('name', '=', filename),
                ('res_field', '=', False),
            ], limit=1)
            if not existing:
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': rec.invoice_file,
                    'res_model': 'solar.quote',
                    'res_id': rec.id,
                })
                rec.message_post(
                    body=_("Factura subida y adjuntada al expediente: <b>%s</b>") % filename,
                    attachment_ids=[attachment.id]
                )

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
            rec.avg_monthly_consumption = total / 12.0
            rec.avg_daily_consumption = (total / 12.0) / 30.0
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
        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
            'cotizador_solar.action_report_solar_proposal', 
            res_ids=self.ids
        )

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

    def action_analyze_invoice(self):
        """ Envía la factura a Google Gemini para extraer el consumo mensual """
        self.ensure_one()
        if not self.invoice_file:
            raise UserError(_("Por favor, adjunte un archivo de factura primero."))
            
        config = self.env['solar.config'].get_config()
        api_key = (config.google_api_key or '').strip()
        
        if not api_key:
            raise UserError(_("La API Key de Google no está configurada. Por favor configúrela en los ajustes del Cotizador Solar."))

        # Extraer mimetype básico según la extensión del archivo
        mime_type = "application/pdf"
        if self.invoice_file_name:
            ext = self.invoice_file_name.lower().split('.')[-1]
            if ext in ['png', 'jpg', 'jpeg']:
                mime_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
            elif ext != 'pdf':
                raise UserError(_("Formato no soportado. Por favor suba un PDF, PNG o JPG."))

        # Preparar el prompt estructurado
        prompt = (
            "Analiza la siguiente factura de energía eléctrica. Extrae la información requerida en un objeto JSON sin markdown:\n"
            "1. Ubica la tabla o gráfico de 'HISTORICO DE CONSUMO' (historial de consumos de kWh).\n"
            "2. Identifica los meses y años de los consumos registrados (normalmente hay hasta 12 meses).\n"
            "3. Ordena los datos estrictamente en ORDEN CRONOLÓGICO, desde el mes MÁS ANTIGUO hasta el mes MÁS RECIENTE (ejemplo: Abril 2025 -> Mayo 2025 -> ... -> Marzo 2026).\n"
            "4. Devuelve el JSON con la siguiente estructura exacta:\n"
            "{\n"
            "  \"start_month_index\": <índice de 0 a 11 del mes MÁS ANTIGUO de la secuencia; 0=Enero, 1=Febrero, 2=Marzo, 3=Abril, 4=Mayo, 5=Junio, 6=Julio, 7=Agosto, 8=Septiembre, 9=Octubre, 10=Noviembre, 11=Diciembre>,\n"
            "  \"start_year\": <año entero de 4 dígitos del mes MÁS ANTIGUO de la secuencia, ej. 2025>,\n"
            "  \"consumption_m1\": <consumo kWh del mes MÁS ANTIGUO>,\n"
            "  \"consumption_m2\": <consumo kWh del 2º mes>,\n"
            "  \"consumption_m3\": <consumo kWh del 3er mes>,\n"
            "  \"consumption_m4\": <consumo kWh del 4º mes>,\n"
            "  \"consumption_m5\": <consumo kWh del 5º mes>,\n"
            "  \"consumption_m6\": <consumo kWh del 6º mes>,\n"
            "  \"consumption_m7\": <consumo kWh del 7º mes>,\n"
            "  \"consumption_m8\": <consumo kWh del 8º mes>,\n"
            "  \"consumption_m9\": <consumo kWh del 9º mes>,\n"
            "  \"consumption_m10\": <consumo kWh del 10º mes>,\n"
            "  \"consumption_m11\": <consumo kWh del 11º mes>,\n"
            "  \"consumption_m12\": <consumo kWh del mes MÁS RECIENTE>,\n"
            "  \"medidor\": <número de medidor si está presente en la factura, de lo contrario null>,\n"
            "  \"nac\": <número de cuenta, NAC o NIC si está presente en la factura, de lo contrario null>\n"
            "}\n"
            "Si algún mes de los 12 no está disponible, asigna 0 en su lugar."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": self.invoice_file.decode('utf-8')
                        }
                    }
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Error al comunicarse con la API de Google: %s" % str(e)))

        data = response.json()
        
        try:
            text_response = data['candidates'][0]['content']['parts'][0]['text']
            json_data = json.loads(text_response)
        except (KeyError, IndexError, json.JSONDecodeError):
            raise UserError(_("Error al procesar la respuesta de la Inteligencia Artificial. La estructura no es la esperada."))

        # Asignar mes y año de inicio si están presentes
        if 'start_month_index' in json_data and json_data['start_month_index'] is not None:
            self.start_month = str(int(json_data['start_month_index']))
        if 'start_year' in json_data and json_data['start_year']:
            self.start_year = int(json_data['start_year'])

        # Asignar medidor y NAC si vienen en la factura y no han sido ingresados manualmente
        if json_data.get('medidor') and not self.medidor:
            self.medidor = str(json_data['medidor'])
        if json_data.get('nac') and not self.nac:
            self.nac = str(json_data['nac'])

        # Asignar los consumos en estricto orden cronológico (Mes 1 = Más Antiguo, Mes 12 = Más Reciente)
        self.consumption_m1 = json_data.get('consumption_m1', 0)
        self.consumption_m2 = json_data.get('consumption_m2', 0)
        self.consumption_m3 = json_data.get('consumption_m3', 0)
        self.consumption_m4 = json_data.get('consumption_m4', 0)
        self.consumption_m5 = json_data.get('consumption_m5', 0)
        self.consumption_m6 = json_data.get('consumption_m6', 0)
        self.consumption_m7 = json_data.get('consumption_m7', 0)
        self.consumption_m8 = json_data.get('consumption_m8', 0)
        self.consumption_m9 = json_data.get('consumption_m9', 0)
        self.consumption_m10 = json_data.get('consumption_m10', 0)
        self.consumption_m11 = json_data.get('consumption_m11', 0)
        self.consumption_m12 = json_data.get('consumption_m12', 0)
        
        # Notificar éxito en el chatter
        self.message_post(body=_("La factura fue analizada con éxito por IA. Consumos (cronológicos) y periodo de inicio (Mes/Año) actualizados."))


