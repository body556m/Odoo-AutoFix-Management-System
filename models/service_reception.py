from odoo import models, fields, api
from odoo.exceptions import UserError


class AutoFixServiceReception(models.Model):
    _name = 'autofix.service.reception'
    _description = 'Service Reception Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
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

    # Invoice fields
    invoice_ids = fields.Many2many('account.move', string='Invoices', copy=False)
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)

    @api.depends('work_order_ids.total_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.work_order_ids.mapped('total_cost'))

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

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

    def action_create_invoice(self):
        """Create customer invoice(s) from done reception(s)."""
        for rec in self:
            if rec.state != 'done':
                raise UserError('Cannot create invoice for reception that is not done.')
            if rec.invoice_count > 0:
                raise UserError('Invoice already exists for reception %s.' % rec.name)

            invoice_lines = []
            # One line per work order (labor cost)
            for wo in rec.work_order_ids:
                if wo.labor_cost > 0:
                    invoice_lines.append((0, 0, {
                        'name': '%s - %s' % (wo.name, wo.description or 'Labor'),
                        'quantity': 1,
                        'price_unit': wo.labor_cost,
                    }))
                # One line per expense on the work order
                for expense in wo.expense_ids:
                    invoice_lines.append((0, 0, {
                        'name': '%s - %s' % (wo.name, expense.description),
                        'quantity': 1,
                        'price_unit': expense.amount,
                    }))

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'invoice_origin': rec.name,
                'invoice_line_ids': invoice_lines,
            })
            rec.invoice_ids = [(4, invoice.id)]

        # If single record and an invoice was actually created, open it
        if len(self) == 1 and self.invoice_ids:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_ids[0].id,
                'target': 'current',
            }

    def action_view_invoices(self):
        """Open related invoices."""
        self.ensure_one()
        if self.invoice_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_ids.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'target': 'current',
        }

    def action_print_invoices(self):
        """Print PDFs for all invoices related to selected receptions."""
        invoices = self.mapped('invoice_ids')
        if not invoices:
            raise UserError('No invoices found for the selected receptions.')
        return self.env.ref('account.account_invoices').report_action(invoices)
