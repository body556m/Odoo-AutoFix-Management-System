from odoo import models, fields, api
from datetime import date


class Warranty(models.Model):
    _name = 'autofix.warranty'
    _description = 'Warranty Record'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    reception_id = fields.Many2one('autofix.service.reception', string='Service Reception')
    work_order_id = fields.Many2one('autofix.work.order', string='Work Order')
    car_id = fields.Many2one('autofix.car', string='Car')
    warranty_type = fields.Selection([
        ('parts', 'Parts'),
        ('labor', 'Labor'),
        ('full', 'Full (Parts + Labor)'),
    ], string='Warranty Type', required=True)
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True)
    duration_months = fields.Integer(string='Duration (Months)', compute='_compute_duration', store=True)
    description = fields.Text(string='Description')
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('claimed', 'Claimed'),
        ('void', 'Void'),
    ], string='Status', default='active')
    claim_ids = fields.One2many('autofix.warranty.claim', 'warranty_id', string='Claims')

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration_months = int(delta.days / 30)
            else:
                record.duration_months = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.warranty') or 'New'
        return super().create(vals_list)

    def action_claim(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Warranty Claim',
            'res_model': 'autofix.warranty.claim',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_warranty_id': self.id},
        }

    @api.model
    def _cron_check_expired(self):
        today = date.today()
        expired = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
        ])
        expired.write({'state': 'expired'})


class WarrantyClaim(models.Model):
    _name = 'autofix.warranty.claim'
    _description = 'Warranty Claim'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    warranty_id = fields.Many2one('autofix.warranty', string='Warranty', required=True)
    claim_date = fields.Date(string='Claim Date', default=fields.Date.context_today, required=True)
    description = fields.Text(string='Issue Description', required=True)
    resolution = fields.Text(string='Resolution')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    claimed_by = fields.Many2one('res.partner', string='Claimed By')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.warranty.claim') or 'New'
        return super().create(vals_list)

    def action_approve(self):
        self.write({'state': 'approved'})
        if self.warranty_id:
            self.warranty_id.write({'state': 'claimed'})

    def action_reject(self):
        self.write({'state': 'rejected'})