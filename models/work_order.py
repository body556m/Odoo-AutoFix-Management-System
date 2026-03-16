from odoo import models, fields, api


class AutoFixWorkOrder(models.Model):
    _name = 'autofix.work.order'
    _description = 'Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    reception_id = fields.Many2one('autofix.service.reception', string='Reception', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='reception_id.partner_id', readonly=True, store=False)
    car_id = fields.Many2one('autofix.car', string='Car', related='reception_id.car_id', readonly=True, store=False)
    employee_id = fields.Many2one('hr.employee', string='Mechanic', required=True)
    description = fields.Text(string='Work Description', required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, tracking=True)
    estimated_hours = fields.Float(string='Estimated Hours')
    actual_hours = fields.Float(string='Actual Hours')
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.work.order') or 'New'
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_to_pending(self):
        for rec in self:
            rec.state = 'pending'
