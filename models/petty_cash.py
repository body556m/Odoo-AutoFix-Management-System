from odoo import models, fields, api


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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.petty.cash') or 'New'
        return super().create(vals_list)
