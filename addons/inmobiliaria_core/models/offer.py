# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EstatePropertyOffer(models.Model):
    _inherit = 'real.estate.property.offer'

    # Tipo de operación
    offer_type = fields.Selection([
        ('sale', 'Compraventa'),
        ('rent', 'Alquiler'),
        ('rent_to_own', 'Alquiler con Opción a Compra'),
        ('swap', 'Permuta'),
    ], string='Tipo de Operación', default='sale', required=True)

    # Para alquileres
    rent_duration = fields.Integer(
        string='Duración Contrato (meses)',
        help='Duración en meses para alquileres'
    )
    rent_adjustment = fields.Selection([
        ('none', 'Sin ajuste'),
        ('icl', 'ICL (Índice Contratos Locación)'),
        ('cpi', 'IPC/Inflación'),
        ('custom', 'Porcentaje Personalizado'),
    ], string='Ajuste Alquiler', default='icl')
    rent_adjustment_value = fields.Float(
        string='% Ajuste Personalizado',
        digits=(5, 2),
        help='Porcentaje anual si es custom'
    )

    # Financiamiento
    financing_type = fields.Selection([
        ('cash', 'Contado'),
        ('mortgage', 'Crédito Hipotecario'),
        ('mixed', 'Mixto (entrega + financiación)'),
        ('owner_financing', 'Financiación Propietario'),
    ], string='Financiamiento', default='cash')
    down_payment = fields.Monetary(
        string='Entrega/Seña',
        currency_field='currency_id',
        help='Monto inicial al firmar boleto/reserva'
    )
    financing_months = fields.Integer(
        string='Plazo Financiación (meses)',
        help='Meses para pagar el saldo'
    )
    financing_rate = fields.Float(
        string='Tasa Financiación Anual (%)',
        digits=(5, 2)
    )

    # Estados extendidos
    status = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Presentada'),
        ('under_review', 'En Revisión'),
        ('counter_offer', 'Contraoferta'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
        ('withdrawn', 'Retirada'),
        ('expired', 'Expirada'),
        ('signed', 'Boleto/Reserva Firmado'),
    ], string='Estado', default='draft', required=True, tracking=True)

    # Fechas clave
    validity_date = fields.Date(
        string='Válida Hasta',
        help='Fecha de expiración de la oferta'
    )
    response_deadline = fields.Date(string='Límite Respuesta')
    signed_date = fields.Date(string='Fecha Firma Boleto')

    # Documentos
    document_ids = fields.One2many(
        'documents.document',
        'res_id',
        domain=[('res_model', '=', 'real.estate.property.offer')],
        string='Documentos (Boleto, Reserva, Recibos)'
    )

    # ============================================================
    # COMPUTES
    # ============================================================

    @api.depends('price', 'property_id')
    def _compute_price_per_m2(self):
        for rec in self:
            if rec.property_id and rec.property_id.area:
                rec.price_per_m2 = rec.price / rec.property_id.area
            else:
                rec.price_per_m2 = 0

    price_per_m2 = fields.Monetary(
        string='Precio/m²',
        compute='_compute_price_per_m2',
        currency_field='currency_id',
        store=True
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    @api.constrains('validity_date')
    def _check_validity_date(self):
        for rec in self:
            if rec.validity_date and rec.validity_date < fields.Date.today():
                if rec.status in ['draft', 'submitted', 'under_review']:
                    rec.status = 'expired'

    @api.constrains('down_payment', 'price')
    def _check_down_payment(self):
        for rec in self:
            if rec.down_payment and rec.price and rec.down_payment > rec.price:
                raise ValidationError(_('La entrega no puede ser mayor al precio total.'))

    # ============================================================
    # ACTIONS
    # ============================================================

    def action_make_counter_offer(self):
        return {
            'name': _('Contraoferta'),
            'type': 'ir.actions.act_window',
            'res_model': 'inmobiliaria.counter.offer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_offer_id': self.id},
        }

    def action_sign_booking(self):
        self.write({
            'status': 'signed',
            'signed_date': fields.Date.today(),
        })
        # Crear actividad para seguimiento
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=_('Seguimiento post-firma boleto'),
            note=_('Verificar documentación y coordinar escritura'),
            user_id=self.env.user.id,
        )
        return True

    def action_send_to_owner(self):
        """Enviar oferta al propietario por email"""
        template = self.env.ref('inmobiliaria_core.email_template_offer_to_owner', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Enviado'),
                'message': _('Oferta enviada al propietario.'),
                'type': 'success',
            }
        }