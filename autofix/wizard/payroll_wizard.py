from odoo import models, fields
from datetime import datetime, date
from pytz import timezone, UTC
import calendar
import logging

_logger = logging.getLogger(__name__)


class AutoFixPayrollWizard(models.TransientModel):
    _name = 'autofix.payroll.wizard'
    _description = 'Generate Payroll'

    month = fields.Integer(
        string='Month', required=True,
        default=lambda self: fields.Date.context_today(self).month,
    )
    year = fields.Integer(
        string='Year', required=True,
        default=lambda self: fields.Date.context_today(self).year,
    )
    bonus_per_wo = fields.Float(
        string='Bonus per Work Order', required=True,
        default=lambda self: float(
            self.env['ir.config_parameter'].sudo().get_param(
                'autofix.bonus_per_wo', '50.0'
            )
        ),
    )

    def action_generate_payroll(self):
        self.ensure_one()

        # ── Step 1: Compute date range ──
        month = self.month
        year = self.year
        date_from = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        date_to = date(year, month, last_day)

        # ── Step 2: Convert to UTC range ──
        admin_user = self.env.ref('base.user_admin')
        user_tz = timezone(admin_user.tz or 'UTC')
        date_from_local = user_tz.localize(
            datetime(date_from.year, date_from.month, date_from.day)
        )
        date_to_local = user_tz.localize(
            datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59)
        )
        date_from_utc = date_from_local.astimezone(UTC).replace(tzinfo=None)
        date_to_utc = date_to_local.astimezone(UTC).replace(tzinfo=None)

        # ── Step 3: Find all active mechanics ──
        employees = self.env['hr.employee'].search([('active', '=', True)])

        # ── Step 4 & 5: Build payroll lines ──
        bonus_per_wo = self.bonus_per_wo
        lines = []

        WorkOrder = self.env['autofix.work.order']
        for emp in employees:
            wo_count = WorkOrder.search_count([
                ('employee_id', '=', emp.id),
                ('state', '=', 'done'),
                ('write_date', '>=', date_from_utc),
                ('write_date', '<', date_to_utc),
            ])

            base_salary = emp.autofix_wage or 0.0
            bonus_total = wo_count * bonus_per_wo

            lines.append({
                'employee_id': emp.id,
                'employee_name': emp.name,
                'job_title': emp.job_title or (
                    emp.job_id.name if emp.job_id else ''
                ),
                'base_salary': base_salary,
                'wo_completed': wo_count,
                'bonus_per_wo': bonus_per_wo,
                'bonus_total': bonus_total,
                'deductions': 0.0,
                'deduction_reason': '',
            })

        # ── Step 6: Create payroll record ──
        line_vals = [(0, 0, line) for line in lines]
        payroll = self.env['autofix.payroll'].create({
            'name': 'New',
            'month': month,
            'year': year,
            'date_from': date_from,
            'date_to': date_to,
            'payroll_line_ids': line_vals,
        })

        # ── Step 7: Persist bonus_per_wo ──
        self.env['ir.config_parameter'].sudo().set_param(
            'autofix.bonus_per_wo', str(bonus_per_wo),
        )

        # ── Step 8: Open the new payroll record ──
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'autofix.payroll',
            'res_id': payroll.id,
            'view_mode': 'form',
            'target': 'current',
        }
