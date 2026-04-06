from odoo import models, fields, api


class InspectionTemplate(models.Model):
    _name = 'autofix.inspection.template'
    _description = 'Vehicle Inspection Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    line_ids = fields.One2many('autofix.inspection.template.line', 'template_id', string='Checklist Items')
    active = fields.Boolean(string='Active', default=True)


class InspectionTemplateLine(models.Model):
    _name = 'autofix.inspection.template.line'
    _description = 'Inspection Template Line'

    template_id = fields.Many2one('autofix.inspection.template', string='Template', required=True)
    name = fields.Char(string='Item Name', required=True)
    category = fields.Selection([
        ('engine', 'Engine'),
        ('brakes', 'Brakes'),
        ('suspension', 'Suspension'),
        ('electrical', 'Electrical'),
        ('body', 'Body'),
        ('tires', 'Tires'),
        ('fluids', 'Fluids'),
        ('interior', 'Interior'),
        ('exterior', 'Exterior'),
    ], string='Category', required=True)
    sequence = fields.Integer(string='Sequence', default=10)


class VehicleInspection(models.Model):
    _name = 'autofix.vehicle.inspection'
    _description = 'Vehicle Inspection'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    reception_id = fields.Many2one('autofix.service.reception', string='Service Reception', required=True)
    inspector_id = fields.Many2one('hr.employee', string='Inspector')
    date = fields.Date(string='Inspection Date', default=fields.Date.context_today, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Completed'),
    ], string='Status', default='draft')
    line_ids = fields.One2many('autofix.vehicle.inspection.line', 'inspection_id', string='Checklist')
    notes = fields.Text(string='Overall Notes')
    overall_condition = fields.Selection([
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('critical', 'Critical'),
    ], string='Overall Condition')
    template_id = fields.Many2one('autofix.inspection.template', string='Template')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.vehicle.inspection') or 'New'
        return super().create(vals_list)

    def action_generate_from_template(self):
        if not self.template_id:
            return
        self.line_ids.unlink()
        lines = []
        for template_line in self.template_id.line_ids.sorted('sequence'):
            lines.append((0, 0, {
                'name': template_line.name,
                'category': template_line.category,
            }))
        self.line_ids = lines

    def action_done(self):
        self.state = 'done'

    def action_reset(self):
        self.state = 'draft'


class VehicleInspectionLine(models.Model):
    _name = 'autofix.vehicle.inspection.line'
    _description = 'Vehicle Inspection Line'

    inspection_id = fields.Many2one('autofix.vehicle.inspection', string='Inspection', required=True)
    name = fields.Char(string='Item Name', required=True)
    category = fields.Selection([
        ('engine', 'Engine'),
        ('brakes', 'Brakes'),
        ('suspension', 'Suspension'),
        ('electrical', 'Electrical'),
        ('body', 'Body'),
        ('tires', 'Tires'),
        ('fluids', 'Fluids'),
        ('interior', 'Interior'),
        ('exterior', 'Exterior'),
    ], string='Category')
    condition = fields.Selection([
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('critical', 'Critical'),
        ('na', 'N/A'),
    ], string='Condition')
    notes = fields.Text(string='Notes')
    photo = fields.Image(string='Photo')
    sequence = fields.Integer(string='Sequence', default=10)