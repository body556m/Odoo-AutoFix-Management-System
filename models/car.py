from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class AutoFixCar(models.Model):
    _name = 'autofix.car'
    _description = 'Registered Cars Data'

    name = fields.Char(string='Plate Number', required=True)
    brand = fields.Char(string='Brand', required=True)
    model = fields.Char(string='Model', required=True)
    year = fields.Integer(string='Year', required=True)
    color = fields.Char(string='Color')
    vin = fields.Char(string='VIN / Chassis')
    mileage = fields.Integer(string='Initial Mileage', required=True)
    partner_id = fields.Many2one('res.partner', string='Owner', required=True, domain=[('customer_rank', '>', 0)])
    reception_ids = fields.One2many('autofix.service.reception', 'car_id', string='Receptions')
    notes = fields.Text(string='Notes')

    @api.depends('name', 'brand', 'model')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.brand and record.model:
                record.display_name = f"[{record.name}] {record.brand} / {record.model}"
            else:
                record.display_name = record.name or ''


    @api.constrains('year')
    def _check_year(self):
        current_year = date.today().year
        for record in self:
            if record.year and (record.year < 1886 or record.year > current_year + 1):
                raise ValidationError("in valid year")
