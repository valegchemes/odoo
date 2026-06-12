# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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