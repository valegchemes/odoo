# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class InmobiliariaNeighborhood(models.Model):
    _name = 'inmobiliaria.neighborhood'
    _description = 'Barrio / Vecindario'
    _order = 'city_id, name'
    _rec_name = 'display_name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Código', size=10, help='Código interno corto')
    city_id = fields.Many2one('res.city', string='Ciudad', required=True)
    state_id = fields.Many2one(
        'res.country.state',
        string='Provincia/Estado',
        related='city_id.state_id',
        store=True
    )
    country_id = fields.Many2one(
        'res.country',
        string='País',
        related='state_id.country_id',
        store=True
    )
    display_name = fields.Char(
        string='Nombre Completo',
        compute='_compute_display_name',
        store=True
    )
    zip_code = fields.Char(string='Código Postal', size=10)
    description = fields.Text(string='Descripción', translate=True)

    # Coordenadas para mapa
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))

    # Stats para reporting
    property_count = fields.Integer(
        string='Propiedades',
        compute='_compute_property_count'
    )
    avg_price_m2 = fields.Monetary(
        string='Precio Promedio m²',
        compute='_compute_avg_price',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    active = fields.Boolean(default=True)
    featured = fields.Boolean(string='Destacado en Web')

    @api.depends('name', 'city_id', 'city_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.city_id:
                rec.display_name = f"{rec.name}, {rec.city_id.name}"
            else:
                rec.display_name = rec.name

    def _compute_property_count(self):
        for rec in self:
            rec.property_count = self.env['real.estate.property'].search_count([
                ('neighborhood_id', '=', rec.id)
            ])

    def _compute_avg_price(self):
        for rec in self:
            props = self.env['real.estate.property'].search([
                ('neighborhood_id', '=', rec.id),
                ('price', '>', 0),
                ('area', '>', 0)
            ])
            if props:
                total_price = sum(p.price for p in props)
                total_area = sum(p.area for p in props)
                rec.avg_price_m2 = total_price / total_area if total_area else 0
            else:
                rec.avg_price_m2 = 0