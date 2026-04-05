from odoo import models, fields


class HrEmployeeAutoFix(models.Model):
    _inherit = 'hr.employee'

    autofix_wage = fields.Float(
        string='Monthly Wage (AutoFix)', default=0.0,
    )
