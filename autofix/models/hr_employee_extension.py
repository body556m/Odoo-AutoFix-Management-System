from odoo import models, fields, api


class HrEmployeeAutoFix(models.Model):
    _inherit = 'hr.employee'

    autofix_wage = fields.Float(
        string='Monthly Wage (AutoFix)', default=0.0,
    )
    specialization = fields.Selection([
        ('mechanical', 'Mechanical'),
        ('electrical', 'Electrical'),
        ('body', 'Body Work'),
        ('paint', 'Paint'),
        ('ac', 'A/C'),
        ('general', 'General'),
    ], string='Specialization')
    skill_level = fields.Selection([
        ('junior', 'Junior'),
        ('senior', 'Senior'),
        ('expert', 'Expert'),
    ], string='Skill Level')
    is_mechanic = fields.Boolean(string='Is Mechanic', default=False)
    work_order_ids = fields.One2many('autofix.work.order', 'employee_id', string='Work Orders')
    work_order_count = fields.Integer(compute='_compute_work_order_count', store=True)
    active_work_order_ids = fields.One2many('autofix.work.order', 'employee_id', string='Active Work Orders', domain=[('state', 'in', ['pending', 'in_progress'])])

    @api.depends('work_order_ids.state')
    def _compute_work_order_count(self):
        for emp in self:
            emp.work_order_count = self.env['autofix.work.order'].search_count([
                ('employee_id', '=', emp.id),
                ('state', '=', 'done'),
            ])
