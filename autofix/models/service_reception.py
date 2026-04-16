from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta


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

    # Service Type and Priority
    service_type_id = fields.Many2one('autofix.service.type', string='Service Type')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0')
    estimated_cost = fields.Float(string='Estimated Cost')

    # Inspections
    inspection_ids = fields.One2many('autofix.vehicle.inspection', 'reception_id', string='Inspections')
    inspection_count = fields.Integer(compute='_compute_inspection_count')

    # Feedback
    feedback_id = fields.Many2one('autofix.customer.feedback', string='Customer Feedback')

    # Invoice fields
    invoice_ids = fields.Many2many('account.move', string='Invoices', copy=False)
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)
    total_labor_cost = fields.Float(string='Total Labor Cost', compute='_compute_total_labor_cost', store=True)

    @api.depends('work_order_ids.total_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.work_order_ids.mapped('total_cost'))

    @api.depends('work_order_ids.labor_cost')
    def _compute_total_labor_cost(self):
        for rec in self:
            rec.total_labor_cost = sum(rec.work_order_ids.mapped('labor_cost'))

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends('inspection_ids')
    def _compute_inspection_count(self):
        for rec in self:
            rec.inspection_count = len(rec.inspection_ids)

    @api.onchange('service_type_id')
    def _onchange_service_type(self):
        if self.service_type_id:
            self.estimated_cost = self.service_type_id.default_labor_cost

    def action_view_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Inspections',
            'res_model': 'autofix.vehicle.inspection',
            'view_mode': 'tree,form',
            'domain': [('reception_id', '=', self.id)],
            'target': 'current',
        }

    def action_request_feedback(self):
        """Send email template to request customer feedback after service is done."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError('Feedback can only be requested for completed receptions.')
        if self.partner_id.email:
            template = self.env.ref('autofix.email_template_customer_feedback', raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)
        return True

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

    def action_print_maintenance_report(self):
        """Print Maintenance Invoice PDF report."""
        records = self.filtered(lambda r: r.invoice_count > 0)
        if not records:
            raise UserError('No receptions with invoices found in the selection.')
        return self.env.ref('autofix.action_report_maintenance_invoice').report_action(records)

    @api.model
    def get_dashboard_data(self):
        """Return all KPI data for the management dashboard."""
        today = date.today()
        first_day_of_month = today.replace(day=1)

        Car = self.env['autofix.car']
        Reception = self.env['autofix.service.reception']
        WorkOrder = self.env['autofix.work.order']
        Invoice = self.env['account.move']
        PettyCash = self.env['autofix.petty.cash']

        # --- KPI counts ---
        total_cars = Car.search_count([])
        today_receptions = Reception.search_count([('date_received', '=', today)])
        open_work_orders = WorkOrder.search_count([('state', 'in', ['pending', 'in_progress'])])
        done_work_orders_month = WorkOrder.search_count([
            ('state', '=', 'done'),
            ('write_date', '>=', first_day_of_month),
            ('write_date', '<=', today),
        ])

        # --- Revenue: paid customer invoices this month ---
        paid_invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('paid', 'in_payment')),
            ('invoice_date', '>=', first_day_of_month),
            ('invoice_date', '<=', today),
        ])
        month_revenue = sum(paid_invoices.mapped('amount_total'))

        # --- Petty Cash this month ---
        petty_records = PettyCash.search([
            ('date', '>=', first_day_of_month),
            ('date', '<=', today),
        ])
        month_petty_cash = sum(petty_records.mapped('amount'))

        # --- Work Order expenses this month ---
        month_work_orders = WorkOrder.search([
            ('create_date', '>=', first_day_of_month),
            ('create_date', '<=', today),
        ])
        month_wo_expenses = sum(month_work_orders.mapped('total_cost'))

        # --- Open Work Orders table ---
        open_wos = WorkOrder.search(
            [('state', 'in', ['pending', 'in_progress'])],
            order='create_date asc',
        )
        open_work_orders_list = []
        for wo in open_wos:
            open_work_orders_list.append({
                'name': wo.name,
                'car': wo.car_id.display_name or '',
                'mechanic': wo.employee_id.name or '',
                'state': wo.state,
                'create_date': wo.create_date.strftime('%Y-%m-%d') if wo.create_date else '',
            })

        # --- Mechanic Performance this month ---
        all_month_wos = WorkOrder.search([
            ('create_date', '>=', first_day_of_month),
            ('create_date', '<=', today),
        ])
        mechanic_data = {}
        for wo in all_month_wos:
            emp_name = wo.employee_id.name or 'Unassigned'
            if emp_name not in mechanic_data:
                mechanic_data[emp_name] = {'done': 0, 'open': 0}
            if wo.state == 'done':
                mechanic_data[emp_name]['done'] += 1
            elif wo.state in ('pending', 'in_progress'):
                mechanic_data[emp_name]['open'] += 1

        mechanic_performance = [
            {'mechanic': name, 'done': vals['done'], 'open': vals['open']}
            for name, vals in mechanic_data.items()
        ]

        # --- Stock Integration: Stock Moves this month ---
        StockMove = self.env['stock.move']
        stock_moves = StockMove.search([
            ('origin', 'ilike', 'WO/'),
        ])
        total_stock_moves = len(stock_moves)
        total_parts_quantity = sum(stock_moves.mapped('product_uom_qty'))

        return {
            'total_cars': total_cars,
            'today_receptions': today_receptions,
            'open_work_orders': open_work_orders,
            'done_work_orders_month': done_work_orders_month,
            'month_revenue': month_revenue,
            'month_petty_cash': month_petty_cash,
            'month_wo_expenses': month_wo_expenses,
            'open_work_orders_list': open_work_orders_list,
            'mechanic_performance': mechanic_performance,
            'stock_integration_count': total_stock_moves,
            'stock_integration_qty': total_parts_quantity,
        }

    # ============================================================
    # Cron Jobs for Unpaid Invoice Management
    # ============================================================

    def _cron_warn_unpaid_invoices(self):
        """
        Cron Job: 15-Day Warning for Unpaid Invoices
        Trigger: daily
        Logic: Find all receptions where:
          - state = 'done'
          - invoice_count > 0
          - date_received is exactly 15 days ago (or more than 15 but less than 30)
          - All linked invoices have payment_state != 'paid'
        Actions:
          1. Post a chatter message on the reception
          2. Send an email to reception.partner_id.email
          3. Create an mail.activity on the reception
        """
        today = fields.Date.today()
        date_15_days_ago = today - timedelta(days=15)
        date_30_days_ago = today - timedelta(days=30)

        # Find receptions: done, with invoices, date between 15-30 days ago
        receptions = self.search([
            ('state', '=', 'done'),
            ('invoice_count', '>', 0),
            ('date_received', '<=', date_15_days_ago),
            ('date_received', '>', date_30_days_ago),
        ])

        for reception in receptions:
            # Check if all linked invoices are unpaid
            unpaid_invoices = reception.invoice_ids.filtered(
                lambda inv: inv.payment_state not in ('paid', 'in_payment')
            )
            if not unpaid_invoices:
                continue

            # Action 1: Post a chatter message
            message_body = (
                "⚠️ Payment Overdue: Invoice for this reception has not been paid.\n"
                f"Reception date: {reception.date_received}. Please follow up with the customer."
            )
            reception.sudo().message_post(body=message_body)

            # Action 2: Send an email to the customer
            if reception.partner_id.email:
                mail_values = {
                    'subject': f"Payment Reminder - {reception.name}",
                    'body_html': f'''
                        <p>Dear {reception.partner_id.name},</p>
                        <p>This is a friendly reminder that your invoice for reception <strong>{reception.name}</strong> 
                        (dated {reception.date_received}) has not been paid yet.</p>
                        <p>Please follow up with us at your earliest convenience to settle the payment.</p>
                        <p>Thank you for your business!</p>
                    ''',
                    'email_from': self.env.user.company_id.email or 'noreply@example.com',
                    'email_to': reception.partner_id.email,
                }
                self.env['mail.mail'].sudo().create(mail_values)

            # Action 3: Create a mail.activity assigned to SUPERUSER
            self.env['mail.activity'].sudo().create({
                'res_id': reception.id,
                'res_model_id': self.env['ir.model']._get('autofix.service.reception').id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': 'Follow up: unpaid invoice over 15 days',
                'user_id': self.env.ref('base.user_admin').id,  # SUPERUSER
            })

    def _cron_cancel_unpaid_invoices(self):
        """
        Cron Job: 30-Day Auto-Cancellation for Unpaid Invoices
        Trigger: daily
        Logic: Find all receptions where:
          - state = 'done'
          - invoice_count > 0
          - date_received is 30 or more days ago
          - All linked invoices have payment_state != 'paid'
        Actions:
          1. Cancel all linked invoices
          2. Set reception.state = 'cancelled'
          3. Post a chatter message on the reception
        """
        today = fields.Date.today()
        date_30_days_ago = today - timedelta(days=30)

        # Find receptions: done, with invoices, date 30+ days ago
        receptions = self.search([
            ('state', '=', 'done'),
            ('invoice_count', '>', 0),
            ('date_received', '<=', date_30_days_ago),
        ])

        for reception in receptions:
            # Check if all linked invoices are unpaid
            unpaid_invoices = reception.invoice_ids.filtered(
                lambda inv: inv.payment_state not in ('paid', 'in_payment')
            )
            if not unpaid_invoices:
                continue

            # Action 1: Cancel all linked invoices
            for invoice in unpaid_invoices:
                if invoice.state != 'cancel':
                    # Check if invoice is posted or draft, then cancel it
                    if invoice.state in ('posted', 'draft'):
                        invoice.sudo().button_cancel()

            # Action 2: Set reception state to cancelled
            reception.sudo().write({'state': 'cancelled'})

            # Action 3: Post a chatter message
            message_body = (
                "🚫 Auto-Cancelled: This reception and its invoice(s) have been "
                "automatically cancelled after 30 days of non-payment."
            )
            reception.sudo().message_post(body=message_body)
