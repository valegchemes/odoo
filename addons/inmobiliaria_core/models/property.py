# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EstateProperty(models.Model):
    _inherit = 'real.estate.property'

    # ============================================================
    # CAMPOS EXTENDIDOS - MERCADO ARGENTINO/LATAM
    # ============================================================

    # Superficies detalladas
    surface_covered = fields.Float(
        string='Superficie Cubierta (m²)',
        digits=(10, 2),
        help='Metros cuadrados cubiertos/construidos'
    )
    surface_uncovered = fields.Float(
        string='Superficie Descubierta (m²)',
        digits=(10, 2),
        help='Metros cuadrados descubiertos (terraza, jardín, patio)'
    )
    surface_total = fields.Float(
        string='Superficie Total (m²)',
        compute='_compute_surface_total',
        store=True,
        digits=(10, 2)
    )

    # Expensas y costos recurrentes
    expenses_amount = fields.Monetary(
        string='Expensas Mensuales',
        currency_field='currency_id',
        help='Expensas ordinarias mensuales'
    )
    expenses_currency_id = fields.Many2one(
        'res.currency',
        related='currency_id',
        string='Moneda Expensas'
    )
    expenses_frequency = fields.Selection([
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('yearly', 'Anual'),
    ], string='Frecuencia Expensas', default='monthly')

    # Servicios e infraestructura
    has_gas = fields.Boolean(string='Gas Natural', default=False)
    has_water = fields.Boolean(string='Agua Corriente', default=True)
    has_electricity = fields.Boolean(string='Electricidad', default=True)
    has_sewage = fields.Boolean(string='Cloacas', default=False)
    has_internet = fields.Boolean(string='Internet/Fibra', default=False)

    # Amenities
    amenity_ids = fields.Many2many(
        'inmobiliaria.amenity',
        string='Amenities',
        help='Servicios y comodidades del edificio/barrio'
    )

    # Cochera
    garage_type = fields.Selection([
        ('none', 'Sin cochera'),
        ('covered', 'Cubierta'),
        ('uncovered', 'Descubierta'),
        ('subsuelo', 'Subsuelo'),
        ('box', 'Box individual'),
    ], string='Tipo de Cochera', default='none')
    garage_included = fields.Boolean(string='Cochera Incluida', default=False)
    garage_price = fields.Monetary(
        string='Precio Cochera (si es separada)',
        currency_field='currency_id'
    )

    # Estado y antigüedad
    construction_year = fields.Integer(
        string='Año de Construcción',
        help='Año de finalización de obra'
    )
    condition = fields.Selection([
        ('new', 'A estrenar / En construcción'),
        ('excellent', 'Excelente'),
        ('good', 'Bueno'),
        ('fair', 'Regular / A refaccionar'),
        ('poor', 'Mal estado'),
    ], string='Estado de Conservación', default='good')

    # Documentación legal
    has_deed = fields.Boolean(string='Escritura/Title', default=False)
    deed_status = fields.Selection([
        ('pending', 'En trámite'),
        ('ready', 'Lista para firmar'),
        ('signed', 'Escriturada'),
        ('mortgage', 'Con hipoteca'),
    ], string='Estado Escritura', default='pending')
    allows_credit = fields.Boolean(string='Acepta Crédito Hipotecario', default=True)
    allows_swap = fields.Boolean(string='Acepta Permuta', default=False)

    # Ubicación detallada
    neighborhood_id = fields.Many2one(
        'inmobiliaria.neighborhood',
        string='Barrio/Vecindario',
        help='Barrio específico para búsquedas geográficas'
    )
    block = fields.Char(string='Manzana', size=10)
    lot = fields.Char(string='Lote', size=10)
    floor = fields.Char(string='Piso', size=10)
    apartment = fields.Char(string='Departamento', size=10)

    # Comercial
    commission_rate = fields.Float(
        string='Comisión Inmobiliaria (%)',
        default=3.0,
        digits=(5, 2),
        help='Porcentaje de comisión sobre precio final'
    )
    commission_fixed = fields.Monetary(
        string='Comisión Fija (opcional)',
        currency_field='currency_id',
        help='Monto fijo si no se usa porcentaje'
    )
    exclusive = fields.Boolean(string='Exclusiva', default=False)
    exclusive_until = fields.Date(string='Exclusiva Hasta')
    published_on_web = fields.Boolean(string='Publicado en Web', default=False)
    featured_on_web = fields.Boolean(string='Destacado en Web', default=False)

    # Relaciones comerciales
    owner_id = fields.Many2one(
        'res.partner',
        string='Propietario',
        domain=[('is_company', '=', False)],
        tracking=True
    )
    owner_phone = fields.Char(related='owner_id.phone', string='Tel. Propietario')
    owner_email = fields.Char(related='owner_id.email', string='Email Propietario')

    # Documentos adjuntos
    document_ids = fields.One2many(
        'documents.document',
        'res_id',
        domain=[('res_model', '=', 'real.estate.property')],
        string='Documentos (Escrituras, Planos, Certificados)'
    )

    # ============================================================
    # COMPUTES & ONCHANGES
    # ============================================================

    @api.depends('surface_covered', 'surface_uncovered')
    def _compute_surface_total(self):
        for rec in self:
            rec.surface_total = (rec.surface_covered or 0) + (rec.surface_uncovered or 0)

    @api.onchange('surface_covered', 'surface_uncovered')
    def _onchange_surfaces(self):
        # Sincroniza con campo nativo 'area' (superficie total)
        if self.surface_covered or self.surface_uncovered:
            self.area = self.surface_total

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    @api.constrains('surface_covered', 'surface_uncovered')
    def _check_surfaces_positive(self):
        for rec in self:
            if rec.surface_covered and rec.surface_covered < 0:
                raise ValidationError(_('La superficie cubierta no puede ser negativa.'))
            if rec.surface_uncovered and rec.surface_uncovered < 0:
                raise ValidationError(_('La superficie descubierta no puede ser negativa.'))

    @api.constrains('construction_year')
    def _check_construction_year(self):
        for rec in self:
            if rec.construction_year and (rec.construction_year < 1800 or rec.construction_year > fields.Date.today().year + 2):
                raise ValidationError(_('Año de construcción inválido (1800-%s).') % (fields.Date.today().year + 2))

    @api.constrains('commission_rate')
    def _check_commission_rate(self):
        for rec in self:
            if rec.commission_rate and (rec.commission_rate < 0 or rec.commission_rate > 100):
                raise ValidationError(_('La comisión debe estar entre 0% y 100%.'))

    # ============================================================
    # ACTIONS
    # ============================================================

    def action_publish_web(self):
        self.write({'published_on_web': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Publicado'),
                'message': _('La propiedad se publicó en el sitio web.'),
                'type': 'success',
            }
        }

    def action_unpublish_web(self):
        self.write({'published_on_web': False, 'featured_on_web': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Despublicado'),
                'message': _('La propiedad se quitó del sitio web.'),
                'type': 'info',
            }
        }

    def action_generate_contract(self):
        """Abrir wizard para generar contrato de reserva/compraventa"""
        return {
            'name': _('Generar Contrato'),
            'type': 'ir.actions.act_window',
            'res_model': 'inmobiliaria.contract.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_property_id': self.id},
        }