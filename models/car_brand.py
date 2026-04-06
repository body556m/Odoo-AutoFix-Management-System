from odoo import models, fields, api

class CarBrand(models.Model):
    _name = 'autofix.car.brand'
    _description = 'Car Brand Master Data'
    _order = 'name'

    name = fields.Char(string='Brand Name', required=True)
    country = fields.Char(string='Country of Origin')
    logo = fields.Binary(string='Logo Image')
    model_ids = fields.One2many('autofix.car.model', 'brand_id', string='Models')
    model_count = fields.Integer(compute='_compute_model_count')

    @api.depends('model_ids')
    def _compute_model_count(self):
        for record in self:
            record.model_count = len(record.model_ids)


class CarModel(models.Model):
    _name = 'autofix.car.model'
    _description = 'Car Model Master Data'
    _order = 'name'

    name = fields.Char(string='Model Name', required=True)
    brand_id = fields.Many2one('autofix.car.brand', string='Brand', required=True)
    car_ids = fields.One2many('autofix.car', 'model_id', string='Cars')
    car_count = fields.Integer(compute='_compute_car_count')

    @api.depends('car_ids')
    def _compute_car_count(self):
        for record in self:
            record.car_count = len(record.car_ids)