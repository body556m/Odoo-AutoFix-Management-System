from odoo import models, fields, api


class AutoFixServiceReception(models.Model):
    _name = 'autofix.service.reception'
    _description = 'Service Reception Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, domain=[('customer_rank', '>', 0)])
    car_id = fields.Many2one('autofix.car', string='Car', required=True, domain="[('partner_id', '=', partner_id)]")
    mileage_on_arrival = fields.Integer(string='Mileage on Arrival', required=True)
    complaint = fields.Text(string='Complaint', required=True)
    date_received = fields.Date(string='Date Received', required=True, default=fields.Date.context_today)
    date_expected = fields.Date(string='Expected Delivery Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    work_order_ids = fields.One2many('autofix.work.order', 'reception_id', string='Work Orders')
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.service.reception') or 'New'
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

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
