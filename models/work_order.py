from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from pytz import timezone, UTC
import logging

_logger = logging.getLogger(__name__)


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
            if not rec.part_ids:
                rec.state = 'done'
                continue

            source_location = self.env.ref('stock.stock_location_stock')
            dest_location = self.env.ref(
                'stock.stock_location_virtual_consumption', False
            ) or self.env.ref('stock.stock_location_customers')

            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id.company_id', '=', self.env.company.id),
            ], limit=1)

            if not picking_type:
                raise UserError('No outgoing picking type found. Configure a warehouse first.')

            picking = self.env['stock.picking'].sudo().create({
                'picking_type_id': picking_type.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'origin': rec.name,
                'company_id': self.env.company.id,
            })

            move_vals = []
            for part in rec.part_ids:
                move_vals.append((0, 0, {
                    'product_id': part.product_id.id,
                    'product_uom_qty': part.quantity,
                    'product_qty': part.quantity,
                    'product_uom': part.product_id.uom_id.id,
                    'name': part.product_id.name,
                    'picking_id': picking.id,
                    'location_id': source_location.id,
                    'location_dest_id': dest_location.id,
                    'company_id': self.env.company.id,
                }))

            picking.sudo().write({'move_ids_without_package': move_vals})
            picking.sudo().action_confirm()
            picking.sudo().action_assign()

            unassigned = picking.move_ids_without_package.filtered(
                lambda m: m.state != 'assigned'
            )
            if unassigned:
                product_names = ', '.join(unassigned.mapped('product_id.name'))
                raise UserError(
                    'Insufficient stock for: %s. '
                    'Please replenish before completing this work order.' % product_names
                )

            for line in picking.move_ids_without_package.mapped('move_line_ids'):
                line.qty_done = line.reserved_uom_qty or line.product_uom_qty

            picking.sudo().button_validate()

            rec.stock_move_ids = [(6, 0, picking.move_ids_without_package.ids)]

            for part in rec.part_ids:
                self.env['autofix.work.order.expense'].sudo().create({
                    'work_order_id': rec.id,
                    'description': part.product_id.name,
                    'amount': part.amount,
                })

            rec._check_reorder_for_parts()

            rec.state = 'done'

    def _check_reorder_for_parts(self):
        """Check reorder rules for all parts and create purchase orders if needed."""
        for rec in self:
            for part in rec.part_ids:
                orderpoints = self.env['stock.warehouse.orderpoint'].search([
                    ('product_id', '=', part.product_id.id)
                ])
                for orderpoint in orderpoints:
                    if part.product_id.qty_available >= orderpoint.product_min_qty:
                        continue
                    sellers = part.product_id.seller_ids
                    if sellers and sellers[0].partner_id:
                        self.env['purchase.order'].sudo().create({
                            'partner_id': sellers[0].partner_id.id,
                            'order_line': [
                                (0, 0, {
                                    'product_id': part.product_id.id,
                                    'product_qty': orderpoint.qty_to_order,
                                    'price_unit': part.product_id.standard_price,
                                })
                            ]
                        })
                    else:
                        rec.message_post(
                            body="No vendor found for %s. Cannot create purchase order."
                                 % part.product_id.name,
                            message_type='notification'
                        )

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_to_pending(self):
        for rec in self:
            rec.state = 'pending'

    # ============================================================
    # Daily Summary Cron
    # ============================================================

    @api.model
    def send_daily_summary(self):
        """Collect today's statistics and send HTML email to all AutoFix managers."""
        # Compute today's range in UTC
        admin_user = self.env.ref('base.user_admin')
        user_tz = timezone(admin_user.tz or 'UTC')
        now_user_tz = datetime.now(user_tz)
        today_start_user = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_user = today_start_user + timedelta(days=1)
        today_start_utc = today_start_user.astimezone(UTC).replace(tzinfo=None)
        today_end_utc = today_end_user.astimezone(UTC).replace(tzinfo=None)
        today_date = now_user_tz.date()
        today_str = today_date.strftime('%d/%m/%Y')

        WorkOrder = self.env['autofix.work.order']
        Invoice = self.env['account.move']

        # ---- Section A: Work Orders Today ----
        wo_new = WorkOrder.search_count([
            ('create_date', '>=', today_start_utc),
            ('create_date', '<', today_end_utc),
        ])
        wo_completed = WorkOrder.search_count([
            ('state', '=', 'done'),
            ('write_date', '>=', today_start_utc),
            ('write_date', '<', today_end_utc),
        ])
        wo_in_progress = WorkOrder.search_count([
            ('state', '=', 'in_progress'),
            ('write_date', '>=', today_start_utc),
            ('write_date', '<', today_end_utc),
        ])
        wo_pending = WorkOrder.search_count([
            ('state', '=', 'pending'),
            ('write_date', '>=', today_start_utc),
            ('write_date', '<', today_end_utc),
        ])
        wo_cancelled = WorkOrder.search_count([
            ('state', '=', 'cancelled'),
            ('write_date', '>=', today_start_utc),
            ('write_date', '<', today_end_utc),
        ])

        # ---- Section B: Financial Summary Today ----
        today_invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('create_date', '>=', today_start_utc),
            ('create_date', '<', today_end_utc),
        ])
        inv_created_count = len(today_invoices)
        inv_total_amount = sum(today_invoices.mapped('amount_total'))

        paid_today_invoices = today_invoices.filtered(
            lambda inv: inv.payment_state == 'paid'
        )
        inv_collected_amount = sum(paid_today_invoices.mapped('amount_total'))

        inv_unpaid_count = Invoice.search_count([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ])
        inv_overdue_count = Invoice.search_count([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('invoice_date_due', '<', today_date),
        ])

        # ---- Section C: Mechanic Performance Today ----
        today_wos = WorkOrder.search([
            '|',
            ('create_date', '>=', today_start_utc),
            ('write_date', '>=', today_start_utc),
        ])
        today_wos = today_wos.filtered(
            lambda wo: wo.create_date < today_end_utc or wo.write_date < today_end_utc
        )

        mechanic_data = {}
        for wo in today_wos:
            emp_name = wo.employee_id.name or 'Unassigned'
            if emp_name not in mechanic_data:
                mechanic_data[emp_name] = {'total': 0, 'completed': 0}
            mechanic_data[emp_name]['total'] += 1
            if wo.state == 'done':
                mechanic_data[emp_name]['completed'] += 1

        if mechanic_data:
            mechanic_rows = [
                {'name': name, 'total': vals['total'], 'completed': vals['completed']}
                for name, vals in sorted(mechanic_data.items())
            ]
        else:
            mechanic_rows = []

        # ---- Section D: Stock Alerts ----
        all_part_lines = self.env['autofix.work.order.part'].search([])
        product_ids = list(set(all_part_lines.mapped('product_id').ids))

        stock_alerts = []
        if product_ids:
            products = self.env['product.product'].browse(product_ids)
            orderpoints = self.env['stock.warehouse.orderpoint'].search([
                ('product_id', 'in', product_ids),
            ])
            orderpoint_map = {op.product_id.id: op.product_min_qty for op in orderpoints}

            for product in products:
                reorder_point = orderpoint_map.get(product.id, 0)
                if reorder_point and product.qty_available < reorder_point:
                    stock_alerts.append({
                        'product_name': product.display_name or product.name,
                        'qty_on_hand': product.qty_available,
                        'reorder_point': reorder_point,
                    })

        # ---- Build HTML email body ----
        body_html = self._build_daily_summary_html(
            today_str, wo_new, wo_completed, wo_in_progress, wo_pending,
            wo_cancelled, inv_created_count, inv_total_amount,
            inv_collected_amount, inv_unpaid_count, inv_overdue_count,
            mechanic_rows, stock_alerts,
        )

        # ---- Send email to all managers ----
        manager_group = self.env.ref('autofix.group_autofix_manager')
        recipients = manager_group.users.filtered(lambda u: u.email)

        if not recipients:
            _logger.warning('AutoFix daily summary: no manager users with email found')
            return

        email_from = (
            self.env.user.company_id.email
            or self.env.user.email
            or 'noreply@example.com'
        )

        for user in recipients:
            mail = self.env['mail.mail'].sudo().create({
                'subject': f'AutoFix Daily Summary \u2014 {today_str}',
                'email_from': email_from,
                'email_to': user.email,
                'body_html': body_html,
                'auto_delete': True,
            })
            mail.send()

        _logger.info(
            'AutoFix daily summary sent to %d manager(s) for %s',
            len(recipients), today_str
        )

    @staticmethod
    def _build_daily_summary_html(
        today_str, wo_new, wo_completed, wo_in_progress, wo_pending,
        wo_cancelled, inv_created_count, inv_total_amount,
        inv_collected_amount, inv_unpaid_count, inv_overdue_count,
        mechanic_rows, stock_alerts,
    ):
        """Build the HTML email body for the daily summary."""
        # Mechanic rows HTML
        if mechanic_rows:
            mechanic_rows_html = ''
            for idx, row in enumerate(mechanic_rows):
                bg = '#ecf0f1' if idx % 2 == 0 else ''
                mechanic_rows_html += (
                    f'<tr style="background-color:{bg};">'
                    f'<td style="padding:8px 15px;border:1px solid #ddd;">{row["name"]}</td>'
                    f'<td style="padding:8px 15px;border:1px solid #ddd;text-align:center;">'
                    f'{row["total"]}</td>'
                    f'<td style="padding:8px 15px;border:1px solid #ddd;text-align:center;'
                    f'font-weight:bold;color:#27ae60;">{row["completed"]}</td></tr>'
                )
            mechanic_section = (
                f'<table style="width:100%;border-collapse:collapse;margin-bottom:25px;'
                f'font-size:14px;">'
                f'<tr style="background-color:#f39c12;color:#fff;">'
                f'<th style="padding:10px 15px;text-align:left;border:1px solid #ddd;">'
                f'Mechanic</th>'
                f'<th style="padding:10px 15px;text-align:center;border:1px solid #ddd;">'
                f'Orders Handled</th>'
                f'<th style="padding:10px 15px;text-align:center;border:1px solid #ddd;">'
                f'Completed</th></tr>'
                f'{mechanic_rows_html}</table>'
            )
        else:
            mechanic_section = (
                '<p style="color:#7f8c8d;font-style:italic;font-size:14px;">'
                'No mechanic activity recorded today</p>'
            )

        # Stock alert rows HTML
        if stock_alerts:
            stock_rows_html = ''
            for idx, alert in enumerate(stock_alerts):
                bg = '#ecf0f1' if idx % 2 == 0 else ''
                stock_rows_html += (
                    f'<tr style="background-color:{bg};">'
                    f'<td style="padding:8px 15px;border:1px solid #ddd;">'
                    f'{alert["product_name"]}</td>'
                    f'<td style="padding:8px 15px;border:1px solid #ddd;text-align:center;'
                    f'color:#e74c3c;font-weight:bold;">{alert["qty_on_hand"]}</td>'
                    f'<td style="padding:8px 15px;border:1px solid #ddd;text-align:center;">'
                    f'{alert["reorder_point"]}</td></tr>'
                )
            stock_section = (
                f'<table style="width:100%;border-collapse:collapse;margin-bottom:25px;'
                f'font-size:14px;">'
                f'<tr style="background-color:#e74c3c;color:#fff;">'
                f'<th style="padding:10px 15px;text-align:left;border:1px solid #ddd;">'
                f'Product</th>'
                f'<th style="padding:10px 15px;text-align:center;border:1px solid #ddd;">'
                f'Current Stock</th>'
                f'<th style="padding:10px 15px;text-align:center;border:1px solid #ddd;">'
                f'Reorder Point</th></tr>'
                f'{stock_rows_html}</table>'
            )
        else:
            stock_section = (
                '<p style="color:#27ae60;font-style:italic;font-size:14px;">'
                'All stock levels are within acceptable range</p>'
            )

        return f'''<div style="max-width:700px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;color:#333;">
    <div style="background-color:#2c3e50;color:#ffffff;padding:20px 30px;text-align:center;">
        <h1 style="margin:0;font-size:24px;">AutoFix Management System</h1>
        <p style="margin:5px 0 0;font-size:14px;opacity:0.9;">Daily Operations Summary</p>
    </div>
    <div style="background-color:#34495e;color:#ffffff;padding:10px 30px;font-size:13px;">
        <strong>Report Date: </strong>{today_str}
    </div>
    <div style="padding:20px 30px;background-color:#f9f9f9;">

    <h2 style="color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:8px;font-size:18px;">Section A &mdash; Work Orders Today</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:25px;font-size:14px;">
        <tr style="background-color:#3498db;color:#fff;">
            <th style="padding:10px 15px;text-align:left;border:1px solid #ddd;">Metric</th>
            <th style="padding:10px 15px;text-align:right;border:1px solid #ddd;">Count</th>
        </tr>
        <tr>
            <td style="padding:8px 15px;border:1px solid #ddd;">New Work Orders</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;">{wo_new}</td>
        </tr>
        <tr style="background-color:#ecf0f1;">
            <td style="padding:8px 15px;border:1px solid #ddd;">Completed</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;color:#27ae60;">{wo_completed}</td>
        </tr>
        <tr>
            <td style="padding:8px 15px;border:1px solid #ddd;">In Progress</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;color:#f39c12;">{wo_in_progress}</td>
        </tr>
        <tr style="background-color:#ecf0f1;">
            <td style="padding:8px 15px;border:1px solid #ddd;">Pending</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;">{wo_pending}</td>
        </tr>
        <tr>
            <td style="padding:8px 15px;border:1px solid #ddd;">Cancelled</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;color:#e74c3c;">{wo_cancelled}</td>
        </tr>
    </table>

    <h2 style="color:#2c3e50;border-bottom:2px solid #27ae60;padding-bottom:8px;font-size:18px;">Section B &mdash; Financial Summary Today</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:25px;font-size:14px;">
        <tr style="background-color:#27ae60;color:#fff;">
            <th style="padding:10px 15px;text-align:left;border:1px solid #ddd;">Metric</th>
            <th style="padding:10px 15px;text-align:right;border:1px solid #ddd;">Value</th>
        </tr>
        <tr>
            <td style="padding:8px 15px;border:1px solid #ddd;">Invoices Created</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;">{inv_created_count}</td>
        </tr>
        <tr style="background-color:#ecf0f1;">
            <td style="padding:8px 15px;border:1px solid #ddd;">Total Amount Invoiced</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;">{inv_total_amount:.2f}</td>
        </tr>
        <tr>
            <td style="padding:8px 15px;border:1px solid #ddd;">Total Amount Collected</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;color:#27ae60;">{inv_collected_amount:.2f}</td>
        </tr>
        <tr style="background-color:#ecf0f1;">
            <td style="padding:8px 15px;border:1px solid #ddd;">Unpaid Invoices</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;color:#f39c12;">{inv_unpaid_count}</td>
        </tr>
        <tr>
            <td style="padding:8px 15px;border:1px solid #ddd;">Overdue Invoices</td>
            <td style="padding:8px 15px;border:1px solid #ddd;text-align:right;font-weight:bold;color:#e74c3c;">{inv_overdue_count}</td>
        </tr>
    </table>

    <h2 style="color:#2c3e50;border-bottom:2px solid #f39c12;padding-bottom:8px;font-size:18px;">Section C &mdash; Mechanic Performance Today</h2>
    {mechanic_section}

    <h2 style="color:#2c3e50;border-bottom:2px solid #e74c3c;padding-bottom:8px;font-size:18px;">Section D &mdash; Stock Alerts</h2>
    {stock_section}

    </div>
    <div style="background-color:#2c3e50;color:#bdc3c7;padding:15px 30px;text-align:center;font-size:12px;">
        This is an automated message generated by AutoFix Management System. Do not reply.
    </div>
</div>'''


class AutoFixWorkOrderExpense(models.Model):
    _name = 'autofix.work.order.expense'
    _description = 'Work Order Expense'

    work_order_id = fields.Many2one('autofix.work.order', string='Work Order', required=True, ondelete='cascade')
    description = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount', required=True)
