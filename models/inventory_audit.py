from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AutoFixInventoryAuditLine(models.Model):
    _name = 'autofix.inventory.audit.line'
    _description = 'Inventory Audit Line'
    _order = 'product_name'

    audit_id = fields.Many2one('autofix.inventory.audit', string='Audit', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    qty_on_hand = fields.Float(string='Qty on Hand', readonly=True)
    reorder_point = fields.Float(string='Reorder Point', readonly=True)
    unit_cost = fields.Float(string='Unit Cost', readonly=True)
    stock_value = fields.Float(string='Stock Value', readonly=True)
    consumed_qty = fields.Float(string='Consumed Qty', readonly=True)
    consumed_value = fields.Float(string='Consumed Value', readonly=True)
    is_low_stock = fields.Boolean(string='Low Stock', readonly=True)


class AutoFixInventoryAudit(models.Model):
    _name = 'autofix.inventory.audit'
    _description = 'Inventory Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, name desc'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    period_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ], string='Period Type', required=True, readonly=True)
    date_from = fields.Date(string='Date From', required=True, readonly=True)
    date_to = fields.Date(string='Date To', required=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)
    confirmed_by = fields.Many2one('res.users', string='Confirmed By', readonly=True)
    confirmed_date = fields.Datetime(string='Confirmed Date', readonly=True)
    notes = fields.Text(string='Notes')

    audit_line_ids = fields.One2many('autofix.inventory.audit.line', 'audit_id', string='Audit Lines')

    total_products_tracked = fields.Integer(string='Total Products', readonly=True)
    total_stock_value = fields.Float(string='Total Stock Value', readonly=True)
    total_consumed_qty = fields.Float(string='Total Consumed Qty', readonly=True)
    total_consumed_value = fields.Float(string='Total Consumed Value', readonly=True)
    low_stock_count = fields.Integer(string='Low Stock Count', readonly=True)

    inv_created_count = fields.Integer(string='Invoices Created', readonly=True)
    inv_total_amount = fields.Float(string='Total Invoiced', readonly=True)
    inv_collected_amount = fields.Float(string='Collected Amount', readonly=True)
    inv_unpaid_amount = fields.Float(string='Unpaid Amount', readonly=True)
    inv_overdue_count = fields.Integer(string='Overdue Count', readonly=True)

    petty_cash_total = fields.Float(string='Petty Cash Total', readonly=True)
    labor_cost_total = fields.Float(string='Labor Cost Total', readonly=True)
    wo_expenses_total = fields.Float(string='Work Order Expenses', readonly=True)
    parts_cost_total = fields.Float(string='Parts Cost Total', readonly=True)
    gross_revenue = fields.Float(string='Gross Revenue', readonly=True)
    total_expenses = fields.Float(string='Total Expenses', readonly=True)
    net_result = fields.Float(string='Net Result', readonly=True)

    wo_total = fields.Integer(string='Total Work Orders', readonly=True)
    wo_completed = fields.Integer(string='Completed', readonly=True)
    wo_cancelled = fields.Integer(string='Cancelled', readonly=True)
    wo_in_progress = fields.Integer(string='In Progress', readonly=True)
    wo_pending = fields.Integer(string='Pending', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.inventory.audit') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            rec.confirmed_by = self.env.user
            rec.confirmed_date = fields.Datetime.now()

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.confirmed_by = False
            rec.confirmed_date = False

    def action_print_report(self):
        return self.env.ref('autofix.action_report_inventory_audit').report_action(self)