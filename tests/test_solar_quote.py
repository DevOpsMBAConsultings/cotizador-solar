# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError

class TestSolarQuote(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Crear un partner para las pruebas
        cls.partner = cls.env['res.partner'].create({
            'name': 'Cliente de Prueba Solar',
            'email': 'cliente.prueba@solar.com',
        })

    def test_01_consumption_stats(self):
        """Verifica que los consumos mensuales se sumen y promedien correctamente."""
        quote = self.env['solar.quote'].create({
            'partner_id': self.partner.id,
            'consumption_m1': 100,
            'consumption_m2': 200,
            'consumption_m3': 300,
            'consumption_m4': 400,
            'consumption_m5': 500,
            'consumption_m6': 600,
            'consumption_m7': 700,
            'consumption_m8': 800,
            'consumption_m9': 900,
            'consumption_m10': 1000,
            'consumption_m11': 1100,
            'consumption_m12': 1200,
        })
        # Suma total = 7800
        self.assertEqual(quote.total_yearly_consumption, 7800.0)
        # Promedio mensual = 7800 / 12 = 650
        self.assertEqual(quote.avg_monthly_consumption, 650.0)
        # Promedio diario = 650 / 30 = 21.666...
        self.assertAlmostEqual(quote.avg_daily_consumption, 21.6666667)
        # Pico = 1200
        self.assertEqual(quote.peak_consumption, 1200.0)
        # Mínimo = 100
        self.assertEqual(quote.min_consumption, 100.0)

    def test_02_quick_calculation_mode(self):
        """Prueba los cálculos automáticos del Modo Rápido."""
        # Creamos una cotización con consumo total de 6000 kWh anuales (500 kWh mensuales promedio)
        # Consumo diario promedio = 500 / 30 = 16.666 kWh
        # Con HSP de 3.5, tamaño de planta teórico = 16.666 / 3.5 = 4.76 kWp
        # Inversión teórica con 0.75 USD/W = 4.76 * 1000 * 0.75 = 3571.42 USD
        # Esto está por encima del mínimo de 3500.0, por lo que no debería aplicar el mínimo
        quote = self.env['solar.quote'].create({
            'partner_id': self.partner.id,
            'mode': 'quick',
            'quick_hsp': 3.5,
            'quick_price': 0.75,
            'quick_min_price': 3500.0,
            'quick_panel_watts': 590.0,
            'quick_min_panels': 8,
            'consumption_m1': 500, 'consumption_m2': 500, 'consumption_m3': 500,
            'consumption_m4': 500, 'consumption_m5': 500, 'consumption_m6': 500,
            'consumption_m7': 500, 'consumption_m8': 500, 'consumption_m9': 500,
            'consumption_m10': 500, 'consumption_m11': 500, 'consumption_m12': 500,
        })
        
        self.assertFalse(quote.is_min_price_applied)
        self.assertFalse(quote.is_min_plant_applied)
        self.assertAlmostEqual(quote.plant_size, 4.76190476)
        self.assertAlmostEqual(quote.investment, 3571.42857)
        self.assertEqual(quote.panel_count, 8) # ceil((4.7619*1000)/590) = 9? Wait: 4761.9 / 590 = 8.07 panels -> int(abs()) = 8 in python int()
        self.assertAlmostEqual(quote.cost_per_watt, 0.75)

    def test_03_advanced_calculation_mode(self):
        """Prueba los cálculos automáticos y el auto-ajuste del Modo Avanzado."""
        quote = self.env['solar.quote'].create({
            'partner_id': self.partner.id,
            'mode': 'advanced',
            'advanced_hsp': 3.5,
            'advanced_efficiency': 100.0,
            'advanced_panel_watts': 600.0,
            'advanced_panel_count': 10,
            'pricing_mode': 'watt',
            'pricing_value': 0.80,
            'advanced_min_price': 3500.0,
            'consumption_m1': 500, 'consumption_m2': 500, 'consumption_m3': 500,
            'consumption_m4': 500, 'consumption_m5': 500, 'consumption_m6': 500,
            'consumption_m7': 500, 'consumption_m8': 500, 'consumption_m9': 500,
            'consumption_m10': 500, 'consumption_m11': 500, 'consumption_m12': 500,
        })
        # Planta = (10 * 600) / 1000 = 6.0 kWp
        self.assertEqual(quote.plant_size, 6.0)
        # Inversión = 6.0 * 1000 * 0.80 = 4800.0
        self.assertEqual(quote.investment, 4800.0)
        
        # Probar auto-ajuste de paneles para el 100% de cobertura
        # Consumo diario promedio = 16.666 kWh
        # Con HSP 3.5 y eff 100%, kWp requerido = 16.666 / 3.5 = 4.76 kWp = 4761.9 Watts
        # Con paneles de 600W, cantidad requerida = ceil(4761.9 / 600) = 8 paneles
        quote.action_auto_size_advanced()
        self.assertEqual(quote.advanced_panel_count, 8)
        self.assertEqual(quote.plant_size, 4.8) # 8 * 600 / 1000

    def test_04_action_generate_proposal(self):
        """Verifica la generación de la propuesta en PDF y el Pedido de Ventas."""
        quote = self.env['solar.quote'].create({
            'partner_id': self.partner.id,
            'mode': 'quick',
            'consumption_m1': 300, 'consumption_m2': 300, 'consumption_m3': 300,
            'consumption_m4': 300, 'consumption_m5': 300, 'consumption_m6': 300,
            'consumption_m7': 300, 'consumption_m8': 300, 'consumption_m9': 300,
            'consumption_m10': 300, 'consumption_m11': 300, 'consumption_m12': 300,
        })

        action = quote.action_generate_proposal()

        # Verificar que se creó el pedido de ventas
        self.assertTrue(quote.sale_order_id)
        sale_order = quote.sale_order_id
        self.assertEqual(sale_order.partner_id, self.partner)
        self.assertEqual(sale_order.origin, quote.name)

        # Verificar que el PDF esté adjunto al pedido de ventas
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', sale_order.id),
        ])
        self.assertEqual(len(attachments), 1)
        self.assertTrue(attachments.datas)
        self.assertTrue(attachments.name.endswith('.pdf'))

        # Verificar el formato de retorno de la acción
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'sale.order')
        self.assertEqual(action.get('res_id'), sale_order.id)

    def test_05_dynamic_default_settings(self):
        """Verifica que los valores por defecto del cotizador se actualicen desde los parámetros del sistema."""
        # 1. Configurar nuevos valores globales por defecto en ir.config_parameter
        self.env['ir.config_parameter'].sudo().set_param('cotizador_solar.default_quick_price', '0.88')
        self.env['ir.config_parameter'].sudo().set_param('cotizador_solar.default_quick_min_price', '4200.0')

        # 2. Crear una nueva cotización solar sin pasar los campos de precio
        quote = self.env['solar.quote'].create({
            'partner_id': self.partner.id,
            'mode': 'quick',
        })

        # 3. Validar que la cotización tome los valores por defecto dinámicos configurados
        self.assertEqual(quote.quick_price, 0.88)
        self.assertEqual(quote.quick_min_price, 4200.0)

    def test_06_solar_config_custom_fields_and_wizard(self):
        """Prueba los campos agregados a solar.config, su validación y la creación de líneas de presupuesto en el wizard."""
        # 1. Probar el decorador @api.constrains en solar.config
        config = self.env['solar.config'].get_config()
        
        # Debe fallar si no tiene [pppp] o [gggg]
        with self.assertRaises(ValidationError):
            config.write({'description_template': 'Plantilla sin etiquetas'})
        with self.assertRaises(ValidationError):
            config.write({'description_template': 'Plantilla con [pppp] pero no la otra'})
        with self.assertRaises(ValidationError):
            config.write({'description_template': 'Plantilla con [gggg] pero no la otra'})
            
        # Debe pasar si tiene ambos
        config.write({'description_template': 'Sistema Solar de [pppp] kWp con generación mensual de [gggg] kWh'})
        self.assertEqual(config.description_template, 'Sistema Solar de [pppp] kWp con generación mensual de [gggg] kWh')

        # Asignar un producto de prueba
        product = self.env['product.product'].create({
            'name': 'Servicio de Instalación Solar Test',
            'type': 'service',
        })
        config.write({'product_id': product.id})

        # 2. Probar la generación de la línea de presupuesto en el wizard
        quote = self.env['solar.quote'].create({
            'partner_id': self.partner.id,
            'mode': 'quick',
            'consumption_m1': 500, 'consumption_m2': 500, 'consumption_m3': 500,
            'consumption_m4': 500, 'consumption_m5': 500, 'consumption_m6': 500,
            'consumption_m7': 500, 'consumption_m8': 500, 'consumption_m9': 500,
            'consumption_m10': 500, 'consumption_m11': 500, 'consumption_m12': 500,
        })
        # Forzar el recálculo
        quote.flush_recordset()

        # Crear plantilla de cotización de prueba si no existe
        template = self.env['sale.order.template'].create({
            'name': 'Plantilla Solar Test',
        })

        wizard = self.env['solar.quote.proposal.wizard'].create({
            'solar_quote_id': quote.id,
            'template_id': template.id,
        })
        
        wizard.action_generate()

        # Verificar que se creó el pedido y que contiene la línea esperada
        self.assertTrue(quote.sale_order_id)
        sale_order = quote.sale_order_id
        
        # Encontrar la línea del producto solar configurado
        solar_line = sale_order.order_line.filtered(lambda l: l.product_id == product)
        self.assertTrue(solar_line)
        self.assertEqual(solar_line.product_uom_qty, 1.0)
        self.assertEqual(solar_line.price_unit, quote.investment)
        
        expected_desc = f'Sistema Solar de {quote.plant_size} kWp con generación mensual de {quote.generation_monthly} kWh'
        self.assertEqual(solar_line.name, expected_desc)
