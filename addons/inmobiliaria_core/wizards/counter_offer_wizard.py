# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class InmobiliariaCounterOfferWizard(models.TransientModel):
    _name = 'inmobiliaria.counter.offer.wizard'
    _description = 'Wizard Contraoferta'

    offer_id = fields.Many2one(
        'real.estate.property.offer',
        string='Oferta Original',
        required=True,
        readonly=True
    )
    property_id = fields.Many2one(
        related='offer_id.property_id',
        string='Propiedad',
        readonly=True
    )
    partner_id = fields.Many2one(
        related='offer_id.partner_id',
        string='Oferente',
        readonly=True
    )
    original_price = fields.Monetary(
        related='offer_id.price',
        string='Precio Original',
        currency_field='currency_id',
        readonly=True
    )
    currency_id = fields.Many2one(related='offer_id.currency_id', readonly=True)

    # Nueva oferta
    counter_price = fields.Monetary(
        string='Precio Contraoferta',
        currency_field='currency_id',
        required=True
    )
    counter_message = fields.Html(string='Mensaje / Justificación')
    valid_until = fields.Date(
        string='Válida Hasta',
        default=lambda self: fields.Date.add(fields.Date.today(), days=7)
    )

    # Opciones
    auto_accept_if_match = fields.Boolean(
        string='Aceptar automáticamente si iguala precio',
        help='Si el oferente acepta este precio, se marca como aceptada automáticamente'
    )

    @api.onchange('original_price')
    def _onchange_original_price(self):
        if self.original_price and not self.counter_price:
            # Sugerir 5-10% arriba del precio original
            self.counter_price = self.original_price * 1.05

    def action_send_counter_offer(self):
        self.ensure_one()
        # Actualizar oferta original a contraoferta
        self.offer_id.write({
            'status': 'counter_offer',
            'price': self.counter_price,
            'validity_date': self.valid_until,
        })

        # Log
        self.offer_id.message_post(
            body=_('Contraoferta enviada: %s (era %s)') % (
                self.counter_price, self.original_price
            ),
            subject=_('Contraoferta en Propiedad %s') % self.property_id.name
        )

        # Notificar al oferente (email)
        template = self.env.ref('inmobiliaria_core.email_template_counter_offer', raise_if_not_found=False)
        if template:
            template.send_mail(self.offer_id.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Contraoferta Enviada'),
                'message': _('Se envió contraoferta de %s al oferente.') % self.counter_price,
                'type': 'success',
            }
        }