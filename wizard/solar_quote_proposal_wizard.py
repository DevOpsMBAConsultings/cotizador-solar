# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SolarQuoteProposalWizard(models.TransientModel):
    _name = 'solar.quote.proposal.wizard'
    _description = 'Asistente de Generación de Propuesta'

    solar_quote_id = fields.Many2one('solar.quote', string='Cotización Solar', required=True)
    template_id = fields.Many2one('sale.order.template', string='Plantilla de Cotización', required=True)

    def action_generate(self):
        self.ensure_one()
        quote = self.solar_quote_id
        if not quote.partner_id:
            raise UserError(_("Por favor, seleccione un cliente antes de generar la propuesta."))

        # 1. Crear el presupuesto de venta (sale.order) asignando la plantilla seleccionada
        sale_order = self.env['sale.order'].create({
            'partner_id': quote.partner_id.id,
            'origin': quote.name,
            'sale_order_template_id': self.template_id.id,
        })
        
        # Cargar las líneas de la plantilla
        if hasattr(sale_order, '_onchange_sale_order_template_id'):
            sale_order._onchange_sale_order_template_id()

        quote.sale_order_id = sale_order.id

        # 2. Generar el PDF usando el motor de reportes de Odoo
        report_template_id = 'cotizador_solar.action_report_solar_proposal'
        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(report_template_id, res_ids=quote.ids)

        # 3. Crear el adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f'Propuesta_Solar_{quote.partner_id.name}_{fields.Date.today()}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'mimetype': 'application/pdf',
        })

        # 4. Registrar en el chatter de la cotización de venta
        sale_order.message_post(
            body=_("Propuesta técnica y económica de solución solar adjuntada automáticamente desde el Cotizador Solar (Ref: %s).", quote.name),
            attachment_ids=[attachment.id]
        )

        # 5. Redireccionar al usuario a la vista de formulario del pedido de venta
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
