from odoo import models, fields, api

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
    partner_id = fields.Many2one('res.partner', string='Owner', required=True)
    reception_ids = fields.One2many('autofix.service.reception', 'car_id', string='Receptions')
    notes = fields.Text(string='Notes')

    def _compute_display_name(self):
        for record in self:
            if record.name and record.brand and record.model:
                record.display_name = f"[{record.name}] {record.brand} / {record.model}"
            else:
                record.display_name = record.name
