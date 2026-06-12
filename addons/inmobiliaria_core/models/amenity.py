# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class InmobiliariaAmenity(models.Model):
    _name = 'inmobiliaria.amenity'
    _description = 'Amenity / Servicio del Edificio o Barrio'
    _order = 'category, sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    description = fields.Text(string='Descripción', translate=True)
    icon = fields.Char(
        string='Icono (FontAwesome)',
        help='Ej: fa-swimming-pool, fa-dumbbell, fa-tree, fa-car, fa-wifi, fa-shield-alt'
    )
    category = fields.Selection([
        ('building', 'Edificio'),
        ('apartment', 'Departamento'),
        ('neighborhood', 'Barrio/Entorno'),
        ('security', 'Seguridad'),
        ('green', 'Espacios Verdes'),
        ('sports', 'Deportes'),
        ('services', 'Servicios'),
        ('transport', 'Transporte'),
    ], string='Categoría', required=True, default='building')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_premium = fields.Boolean(string='Premium', help='Amenity de alto valor (pileta, gimnasio, SUM)')

    property_ids = fields.Many2many(
        'real.estate.property',
        string='Propiedades',
        relation='property_amenity_rel',
        column1='amenity_id',
        column2='property_id'
    )