from odoo import models, fields, api
from datetime import datetime, timedelta
from pytz import timezone, UTC
import logging

_logger = logging.getLogger(__name__)


class AutoFixInventoryAuditWizard(models.TransientModel):
    _name = 'autofix.inventory.audit.wizard'
    _description = 'Generate Inventory Audit'

    period_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ], string='Period Type', required=True, default='monthly')
    reference_date = fields.Date(string='Reference Date', required=True, default=fields.Date.context_today)

    def action_generate_audit(self):
        self.ensure_one()
        
        ref_date = self.reference_date
        period_type = self.period_type

        if period_type == 'monthly':
            date_from = ref_date.replace(day=1)
            if ref_date.month == 12:
                date_to = ref_date.replace(year=ref_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                date_to = ref_date.replace(month=ref_date.month + 1, day=1) - timedelta(days=1)
        else:
            date_from = ref_date.replace(month=1, day=1)
            date_to = ref_date.replace(month=12, day=31)

        admin_user = self.env.ref('base.user_admin')
        user_tz = timezone(admin_user.tz or 'UTC')
        date_from_user = user_tz.localize(datetime(date_from.year, date_from.month, date_from.day))
        date_to_user = user_tz.localize(datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59))
        date_from_utc = date_from_user.astimezone(UTC).replace(tzinfo=None)
        date_to_utc = date_to_user.astimezone(UTC).replace(tzinfo=None)

        all_part_lines = self.env['autofix.work.order.part'].search([])
        product_ids = list(set(all_part_lines.mapped('product_id').ids))

        products = self.env['product.product'].browse(product_ids)
        orderpoints = self.env['stock.warehouse.orderpoint'].search([('product_id', 'in', product_ids)])
        orderpoint_map = {op.product_id.id: op.product_min_qty for op in orderpoints}

        stock_moves = self.env['stock.move'].search([
            ('origin', 'ilike', 'WO/'),
            ('state', '=', 'done'),
            ('date', '>=', date_from_utc),
            ('date', '<=', date_to_utc),
        ])
        consumed_map = {}
        for move in stock_moves:
            pid = move.product_id.id
            consumed_map[pid] = consumed_map.get(pid, 0.0) + move.product_uom_qty

        audit_lines = []
        total_products = 0
        total_stock_value = 0.0
        total_consumed_qty = 0.0
        total_consumed_value = 0.0
        low_stock_count = 0

        for product in products:
            qty_on_hand = product.qty_available or 0.0
            reorder_point = orderpoint_map.get(product.id, 0)
            unit_cost = product.standard_price or 0.0
            stock_val = qty_on_hand * unit_cost
            consumed_qty = consumed_map.get(product.id, 0.0)
            consumed_val = consumed_qty * unit_cost
            is_low = bool(reorder_point and qty_on_hand < reorder_point)

            if is_low:
                low_stock_count += 1

            audit_lines.append({
                'product_id': product.id,
                'product_name': product.display_name or product.name,
                'qty_on_hand': qty_on_hand,
                'reorder_point': reorder_point,
                'unit_cost': unit_cost,
                'stock_value': stock_val,
                'consumed_qty': consumed_qty,
                'consumed_value': consumed_val,
                'is_low_stock': is_low,
            })

            total_products += 1
            total_stock_value += stock_val
            total_consumed_qty += consumed_qty
            total_consumed_value += consumed_val

        domain = [('move_type', '=', 'out_invoice'), ('create_date', '>=', date_from_utc), ('create_date', '<=', date_to_utc)]
        inv_created = self.env['account.move'].search(domain)
        inv_created_count = len(inv_created)
        inv_total_amount = sum(inv_created.mapped('amount_total'))
        paid_invoices = inv_created.filtered(lambda inv: inv.payment_state == 'paid')
        inv_collected_amount = sum(paid_invoices.mapped('amount_total'))
        unpaid_invoices = inv_created.filtered(lambda inv: inv.payment_state in ('not_paid', 'partial'))
        inv_unpaid_amount = sum(unpaid_invoices.mapped('amount_total'))
        today = fields.Date.context_today(self)
        overdue_invoices = unpaid_invoices.filtered(lambda inv: inv.invoice_date_due and inv.invoice_date_due < today)
        inv_overdue_count = len(overdue_invoices)

        petty_cash_records = self.env['autofix.petty.cash'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])
        petty_cash_total = sum(petty_cash_records.mapped('amount'))

        work_orders = self.env['autofix.work.order'].search([
            ('create_date', '>=', date_from_utc),
            ('create_date', '<=', date_to_utc),
        ])
        labor_cost_total = sum(work_orders.mapped('labor_cost'))
        wo_expenses_total = sum(work_orders.mapped('total_expenses'))
        parts_cost_total = sum(work_orders.mapped('total_parts_cost'))

        wo_total = len(work_orders)
        wo_completed = work_orders.filtered(lambda wo: wo.state == 'done')
        wo_cancelled = work_orders.filtered(lambda wo: wo.state == 'cancelled')
        wo_in_progress = work_orders.filtered(lambda wo: wo.state == 'in_progress')
        wo_pending = work_orders.filtered(lambda wo: wo.state == 'pending')

        gross_revenue = inv_collected_amount
        total_expenses = petty_cash_total + labor_cost_total + wo_expenses_total + parts_cost_total
        net_result = gross_revenue - total_expenses

        audit_vals = {
            'name': 'New',
            'period_type': period_type,
            'date_from': date_from,
            'date_to': date_to,
            'total_products_tracked': total_products,
            'total_stock_value': total_stock_value,
            'total_consumed_qty': total_consumed_qty,
            'total_consumed_value': total_consumed_value,
            'low_stock_count': low_stock_count,
            'inv_created_count': inv_created_count,
            'inv_total_amount': inv_total_amount,
            'inv_collected_amount': inv_collected_amount,
            'inv_unpaid_amount': inv_unpaid_amount,
            'inv_overdue_count': inv_overdue_count,
            'petty_cash_total': petty_cash_total,
            'labor_cost_total': labor_cost_total,
            'wo_expenses_total': wo_expenses_total,
            'parts_cost_total': parts_cost_total,
            'gross_revenue': gross_revenue,
            'total_expenses': total_expenses,
            'net_result': net_result,
            'wo_total': wo_total,
            'wo_completed': len(wo_completed),
            'wo_cancelled': len(wo_cancelled),
            'wo_in_progress': len(wo_in_progress),
            'wo_pending': len(wo_pending),
        }

        line_vals = [(0, 0, line) for line in audit_lines]
        audit_vals['audit_line_ids'] = line_vals

        audit = self.env['autofix.inventory.audit'].create(audit_vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'autofix.inventory.audit',
            'res_id': audit.id,
            'view_mode': 'form',
            'target': 'current',
        }