from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustomerFeedback(models.Model):
    _name = 'autofix.customer.feedback'
    _description = 'Customer Feedback'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    reception_id = fields.Many2one('autofix.service.reception', string='Service Reception', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', related='reception_id.partner_id', store=True)
    rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], string='Rating', required=True)
    service_quality = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ], string='Service Quality')
    cleanliness = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ], string='Cleanliness')
    timeliness = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor'),
    ], string='Timeliness')
    comment = fields.Text(string='Comments')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    would_recommend = fields.Boolean(string='Would Recommend', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.customer.feedback') or 'New'
        return super().create(vals_list)

    @api.constrains('reception_id')
    def _check_unique_feedback(self):
        for record in self:
            existing = self.search([('reception_id', '=', record.reception_id.id), ('id', '!=', record.id)])
            if existing:
                raise ValidationError('Feedback already exists for this reception.')