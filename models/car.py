from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class AutoFixCar(models.Model):
    _name = 'autofix.car'
    _description = 'Registered Cars Data'

    name = fields.Char(string='Plate Number', required=True)
    brand_id = fields.Many2one('autofix.car.brand', string='Brand', required=True)
    model_id = fields.Many2one('autofix.car.model', string='Model', required=True)
    year = fields.Integer(string='Year', required=True)
    color = fields.Char(string='Color')
    vin = fields.Char(string='VIN / Chassis')
    mileage = fields.Integer(string='Initial Mileage', required=True)
    partner_id = fields.Many2one('res.partner', string='Owner', required=True)
    reception_ids = fields.One2many('autofix.service.reception', 'car_id', string='Receptions')
    notes = fields.Text(string='Notes')
    fuel_type = fields.Selection([
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
        ('gas', 'LPG/CNG'),
    ], string='Fuel Type')
    transmission = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
    ], string='Transmission')
    engine_number = fields.Char(string='Engine Number')
    engine_size = fields.Char(string='Engine Size')
    insurance_company = fields.Char(string='Insurance Company')
    insurance_expiry = fields.Date(string='Insurance Expiry Date')
    car_image = fields.Image(string='Car Image')
    service_count = fields.Integer(compute='_compute_service_count', store=True)

    @api.depends('reception_ids')
    def _compute_service_count(self):
        for record in self:
            record.service_count = len(record.reception_ids)

    @api.depends('name', 'brand_id', 'model_id')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.brand_id and record.model_id:
                record.display_name = f"[{record.name}] {record.brand_id.name} / {record.model_id.name}"
            else:
                record.display_name = record.name or ''

    @api.constrains('year')
    def _check_year(self):
        current_year = date.today().year
        for record in self:
            if record.year and (record.year < 1886 or record.year > current_year + 1):
                raise ValidationError("Invalid year")
