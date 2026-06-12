# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstatePropertyType(models.Model):
    _inherit = 'real.estate.property.type'

    # Categorización extendida
    category = fields.Selection([
        ('residential', 'Residencial'),
        ('commercial', 'Comercial'),
        ('industrial', 'Industrial'),
        ('land', 'Terreno/Lote'),
        ('other', 'Otros'),
    ], string='Categoría Principal', default='residential', required=True)

    # Para reporting
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Icono para web
    icon = fields.Char(
        string='Icono (FontAwesome)',
        help='Ej: fa-home, fa-building, fa-warehouse, fa-tree, fa-map-marker'
    )
    color = fields.Integer(string='Color Índice', default=0)

    _order = 'category, sequence, name'


class EstatePropertyTag(models.Model):
    _inherit = 'real.estate.property.tag'

    # Categorías de tags
    tag_category = fields.Selection([
        ('feature', 'Característica'),
        ('location', 'Ubicación'),
        ('condition', 'Estado'),
        ('legal', 'Legal'),
        ('financial', 'Financiero'),
    ], string='Categoría', default='feature', required=True)

    # Para filtros web
    is_filterable = fields.Boolean(string='Filtrado en Web', default=True)
    show_on_card = fields.Boolean(string='Mostrar en Tarjeta', default=True)