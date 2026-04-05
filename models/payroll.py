from odoo import models, fields, api


class AutoFixPayroll(models.Model):
    _name = 'autofix.payroll'
    _description = 'AutoFix Monthly Payroll'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, month desc, id desc'

    name = fields.Char(
        string='Reference', readonly=True, default='New', copy=False,
    )
    month = fields.Integer(
        string='Month', required=True,
    )
    year = fields.Integer(
        string='Year', required=True,
    )
    period_label = fields.Char(
        string='Period', compute='_compute_period_label', store=True,
    )
    date_from = fields.Date(string='Date From', readonly=True)
    date_to = fields.Date(string='Date To', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', required=True, tracking=True)
    confirmed_by = fields.Many2one(
        'res.users', string='Confirmed By', readonly=True,
    )
    confirmed_date = fields.Datetime(
        string='Confirmed Date', readonly=True,
    )
    notes = fields.Text(string='Notes')
    payroll_line_ids = fields.One2many(
        'autofix.payroll.line', 'payroll_id', string='Payroll Lines',
    )

    total_base_salary = fields.Float(
        string='Total Base Salary', compute='_compute_totals', store=True,
    )
    total_bonus = fields.Float(
        string='Total Bonus', compute='_compute_totals', store=True,
    )
    total_deductions = fields.Float(
        string='Total Deductions', compute='_compute_totals', store=True,
    )
    total_net = fields.Float(
        string='Total Net Salary', compute='_compute_totals', store=True,
    )
    wo_count_total = fields.Integer(
        string='Total Work Orders', compute='_compute_totals', store=True,
    )

    @api.depends(
        'payroll_line_ids.base_salary',
        'payroll_line_ids.bonus_total',
        'payroll_line_ids.deductions',
        'payroll_line_ids.net_salary',
        'payroll_line_ids.wo_completed',
    )
    def _compute_totals(self):
        for rec in self:
            lines = rec.payroll_line_ids
            rec.total_base_salary = sum(lines.mapped('base_salary'))
            rec.total_bonus = sum(lines.mapped('bonus_total'))
            rec.total_deductions = sum(lines.mapped('deductions'))
            rec.total_net = sum(lines.mapped('net_salary'))
            rec.wo_count_total = sum(lines.mapped('wo_completed'))

    @api.depends('month', 'year')
    def _compute_period_label(self):
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December',
        }
        for rec in self:
            if rec.month and rec.year:
                rec.period_label = '%s %s' % (
                    month_names.get(rec.month, ''), rec.year,
                )
            else:
                rec.period_label = ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'autofix.payroll'
                ) or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.write({
                'state': 'confirmed',
                'confirmed_by': self.env.uid,
                'confirmed_date': fields.Datetime.now(),
            })

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft',
                'confirmed_by': False,
                'confirmed_date': False,
            })

    def action_print_report(self):
        return self.env.ref(
            'autofix.action_report_payroll'
        ).report_action(self)


class AutoFixPayrollLine(models.Model):
    _name = 'autofix.payroll.line'
    _description = 'AutoFix Payroll Line'

    payroll_id = fields.Many2one(
        'autofix.payroll', string='Payroll', required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', readonly=True,
    )
    employee_name = fields.Char(string='Employee Name')
    job_title = fields.Char(string='Job Title')
    base_salary = fields.Float(string='Base Salary', readonly=True)
    wo_completed = fields.Integer(
        string='WOs Completed', readonly=True,
    )
    bonus_per_wo = fields.Float(string='Bonus per WO', readonly=True)
    bonus_total = fields.Float(string='Total Bonus', readonly=True)
    deductions = fields.Float(string='Deductions')
    deduction_reason = fields.Char(string='Deduction Reason')
    net_salary = fields.Float(
        string='Net Salary', compute='_compute_net_salary', store=True,
    )

    @api.depends('base_salary', 'bonus_total', 'deductions')
    def _compute_net_salary(self):
        for rec in self:
            rec.net_salary = rec.base_salary + rec.bonus_total - rec.deductions
