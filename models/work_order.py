from odoo import models, fields, api
from odoo.exceptions import UserError


class AutoFixWorkOrderPart(models.Model):
    _name = 'autofix.work.order.part'
    _description = 'Work Order Part'

    work_order_id = fields.Many2one('autofix.work.order', string='Work Order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Part', required=True, domain=[('type', 'in', ['product', 'consu'])])
    quantity = fields.Float(string='Quantity Used', required=True, default=1.0)
    unit_price = fields.Float(string='Unit Price', compute='_compute_unit_price', store=True)
    amount = fields.Float(string='Total', compute='_compute_amount', store=True)

    @api.depends('product_id')
    def _compute_unit_price(self):
        for rec in self:
            rec.unit_price = rec.product_id.standard_price or 0.0

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.unit_price


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
    part_ids = fields.One2many('autofix.work.order.part', 'work_order_id', string='Parts Used')
    total_parts_cost = fields.Float(string='Total Parts Cost', compute='_compute_total_parts_cost', store=True)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)
    stock_move_ids = fields.Many2many('stock.move', string='Stock Moves', copy=False)

    @api.depends('expense_ids.amount')
    def _compute_total_expenses(self):
        for rec in self:
            rec.total_expenses = sum(rec.expense_ids.mapped('amount'))

    @api.depends('part_ids.amount')
    def _compute_total_parts_cost(self):
        for rec in self:
            rec.total_parts_cost = sum(rec.part_ids.mapped('amount'))

    @api.depends('labor_cost', 'total_expenses', 'total_parts_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.labor_cost + rec.total_expenses + rec.total_parts_cost

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
            # Process parts - create stock moves and expenses
            for part in rec.part_ids:
                try:
                    # Get source and destination locations
                    source_location = self.env.ref('stock.stock_location_stock')
                    # Try virtual consumption location, fallback to customers
                    dest_location = self.env.ref('stock.stock_location_virtual_consumption', False)
                    if not dest_location:
                        dest_location = self.env.ref('stock.stock_location_customers')

                    # Create stock move using sudo()
                    stock_move = self.env['stock.move'].sudo().create({
                        'product_id': part.product_id.id,
                        'product_uom_qty': part.quantity,
                        'product_uom': part.product_id.uom_id.id,
                        'name': 'AutoFix WO: %s' % rec.name,
                        'location_id': source_location.id,
                        'location_dest_id': dest_location.id,
                        'state': 'draft',
                    })

                    # Confirm and validate the move
                    stock_move._action_confirm()
                    stock_move._action_done()

                    # Link stock move to work order
                    rec.stock_move_ids = [(4, stock_move.id)]

                except Exception as e:
                    # Log failure to chatter but don't prevent completion
                    rec.message_post(
                        body=f"Failed to create stock move for {part.product_id.name}: {str(e)}",
                        message_type='notification'
                    )
                    continue

                # Create expense for the part
                try:
                    self.env['autofix.work.order.expense'].sudo().create({
                        'work_order_id': rec.id,
                        'description': part.product_id.name,
                        'amount': part.amount,
                    })
                except Exception as e:
                    rec.message_post(
                        body=f"Failed to create expense for {part.product_id.name}: {str(e)}",
                        message_type='notification'
                    )

                # Check reorder rules for the product
                try:
                    orderpoints = self.env['stock.warehouse.orderpoint'].search([
                        ('product_id', '=', part.product_id.id)
                    ])
                    for orderpoint in orderpoints:
                        # Check if quantity after move is below minimum
                        if part.product_id.qty_available < orderpoint.product_min_qty:
                            # Try to create purchase order
                            sellers = part.product_id.seller_ids
                            if sellers and sellers[0].partner_id:
                                # Create purchase order
                                po_vals = {
                                    'partner_id': sellers[0].partner_id.id,
                                    'order_line': [
                                        (0, 0, {
                                            'product_id': part.product_id.id,
                                            'product_qty': orderpoint.qty_to_order,
                                            'price_unit': part.product_id.standard_price,
                                        })
                                    ]
                                }
                                self.env['purchase.order'].sudo().create(po_vals)
                            else:
                                rec.message_post(
                                    body=f"No vendor found for {part.product_id.name}. Cannot create purchase order.",
                                    message_type='notification'
                                )
                except Exception as e:
                    rec.message_post(
                        body=f"Failed to process reorder rule for {part.product_id.name}: {str(e)}",
                        message_type='notification'
                    )

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
