# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class InmobiliariaContractWizard(models.TransientModel):
    _name = 'inmobiliaria.contract.wizard'
    _description = 'Wizard Generar Contrato/Reserva'

    property_id = fields.Many2one(
        'real.estate.property',
        string='Propiedad',
        required=True,
        readonly=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Comprador/Inquilino',
        required=True,
        domain=[('is_company', '=', False)]
    )
    contract_type = fields.Selection([
        ('booking', 'Reserva / Seña'),
        ('boleto', 'Boleto Compraventa'),
        ('rental', 'Contrato de Alquiler'),
        ('swap', 'Permuta'),
    ], string='Tipo de Contrato', required=True, default='booking')

    # Montos
    amount = fields.Monetary(
        string='Monto',
        currency_field='currency_id',
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    payment_method = fields.Selection([
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia'),
        ('check', 'Cheque'),
        ('mixed', 'Mixto'),
    ], string='Forma de Pago', default='transfer')

    # Fechas
    signing_date = fields.Date(
        string='Fecha Firma',
        default=fields.Date.today,
        required=True
    )
    expiration_date = fields.Date(string='Vencimiento Reserva')

    # Condiciones
    conditions = fields.Html(string='Condiciones Particulares')
    subject_to_credit = fields.Boolean(string='Sujeto a Crédito Hipotecario')
    subject_to_sale = fields.Boolean(string='Sujeto a Venta Propiedad Actual')

    # Documento generado
    template_id = fields.Many2one(
        'sign.template',
        string='Plantilla de Contrato',
        domain=[('model_id.model', '=', 'real.estate.property')]
    )

    @api.onchange('property_id', 'contract_type')
    def _onchange_property_contract(self):
        if self.property_id:
            if self.contract_type == 'booking':
                self.amount = self.property_id.price * 0.05  # 5% seña
            elif self.contract_type == 'boleto':
                self.amount = self.property_id.price * 0.30  # 30% boleto
            elif self.contract_type == 'rental':
                self.amount = self.property_id.rent_price or 0

    def action_generate(self):
        self.ensure_one()
        # Crear sign.request para firma digital
        if self.template_id:
            sign_request = self.env['sign.request'].create({
                'template_id': self.template_id.id,
                'reference': f"{self.contract_type.upper()}-{self.property_id.name}-{fields.Date.today()}",
                'request_item_ids': [
                    (0, 0, {
                        'partner_id': self.partner_id.id,
                        'role_id': self.template_id.sign_item_ids[0].role_id.id if self.template_id.sign_item_ids else False,
                    }),
                    (0, 0, {
                        'partner_id': self.property_id.owner_id.id or self.env.user.partner_id.id,
                        'role_id': self.template_id.sign_item_ids[1].role_id.id if len(self.template_id.sign_item_ids) > 1 else False,
                    }),
                ],
            })
            # Log en chatter
            self.property_id.message_post(
                body=_('Contrato %s generado para %s por %s') % (
                    dict(self._fields['contract_type']._description_selection(self.env)).get(self.contract_type),
                    self.partner_id.name,
                    self.amount
                ),
                subject=_('Nuevo Contrato: %s') % self.contract_type
            )
            return {
                'name': _('Firmar Contrato'),
                'type': 'ir.actions.act_window',
                'res_model': 'sign.request',
                'res_id': sign_request.id,
                'view_mode': 'form',
                'target': 'current',
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuración requerida'),
                'message': _('No hay plantilla de contrato configurada. Vaya a Configuración > Firmas > Plantillas.'),
                'type': 'warning',
            }
        }