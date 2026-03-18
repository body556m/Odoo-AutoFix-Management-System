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
    labor_cost = fields.Float(string='Labor Cost')
    expense_ids = fields.One2many('autofix.work.order.expense', 'work_order_id', string='Expenses')
    total_expenses = fields.Float(string='Total Expenses', compute='_compute_total_expenses', store=True)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)

    @api.depends('expense_ids.amount')
    def _compute_total_expenses(self):
        for rec in self:
            rec.total_expenses = sum(rec.expense_ids.mapped('amount'))

    @api.depends('labor_cost', 'total_expenses')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.labor_cost + rec.total_expenses

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



class AutoFixWorkOrderExpense(models.Model):
    _name = 'autofix.work.order.expense'
    _description = 'Work Order Expense'

    work_order_id = fields.Many2one('autofix.work.order', string='Work Order', required=True, ondelete='cascade')
    description = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount', required=True)
