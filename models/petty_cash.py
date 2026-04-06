from odoo import models, fields, api
from odoo.exceptions import UserError


class AutoFixPettyCash(models.Model):
    _name = 'autofix.petty.cash'
    _description = 'Petty Cash Expenses'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    category = fields.Selection([
        ('supplies', 'Supplies'),
        ('maintenance', 'Maintenance'),
        ('utilities', 'Utilities'),
        ('other', 'Other'),
    ], string='Category', required=True)
    description = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount', required=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('network', 'Network'),
    ], string='Payment Method', required=True)
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', readonly=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    responsible_id = fields.Many2one('hr.employee', string='Responsible Person')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.petty.cash') or 'New'
        return super().create(vals_list)

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft records can be approved.')
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_reject(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft records can be rejected.')
            rec.write({'state': 'rejected'})

    def action_reset(self):
        for rec in self:
            rec.write({'state': 'draft', 'approved_by': False, 'approved_date': False})
