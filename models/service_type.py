from odoo import models, fields, api

class ServiceType(models.Model):
    _name = 'autofix.service.type'
    _description = 'Service Type Master Data'
    _order = 'name'

    name = fields.Char(string='Service Name', required=True)
    category = fields.Selection([
        ('mechanical', 'Mechanical'),
        ('electrical', 'Electrical'),
        ('body', 'Body Work'),
        ('paint', 'Paint'),
        ('ac', 'A/C'),
        ('tires', 'Tires & Wheels'),
        ('general', 'General Maintenance'),
    ], string='Category', required=True)
    default_labor_cost = fields.Float(string='Default Labor Cost')
    estimated_duration = fields.Float(string='Estimated Duration (Hours)')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    reception_ids = fields.One2many('autofix.service.reception', 'service_type_id', string='Receptions')
    reception_count = fields.Integer(compute='_compute_reception_count')

    @api.depends('reception_ids')
    def _compute_reception_count(self):
        for record in self:
            record.reception_count = len(record.reception_ids)