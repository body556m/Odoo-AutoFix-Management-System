from odoo import models, fields, api
from datetime import datetime, timedelta


class Appointment(models.Model):
    _name = 'autofix.appointment'
    _description = 'Customer Appointment'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, default='New', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    car_id = fields.Many2one('autofix.car', string='Car', domain="[('partner_id', '=', partner_id)]")
    service_type_id = fields.Many2one('autofix.service.type', string='Service Type')
    appointment_date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    time_slot = fields.Selection([
        ('08:00', '08:00 - 09:00'),
        ('09:00', '09:00 - 10:00'),
        ('10:00', '10:00 - 11:00'),
        ('11:00', '11:00 - 12:00'),
        ('12:00', '12:00 - 13:00'),
        ('13:00', '13:00 - 14:00'),
        ('14:00', '14:00 - 15:00'),
        ('15:00', '15:00 - 16:00'),
        ('16:00', '16:00 - 17:00'),
        ('17:00', '17:00 - 18:00'),
    ], string='Time Slot', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('arrived', 'Arrived'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', default='draft')
    reception_id = fields.Many2one('autofix.service.reception', string='Created Reception')
    notes = fields.Text(string='Notes')
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('autofix.appointment') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_arrived(self):
        self.ensure_one()
        reception = self.env['autofix.service.reception'].create({
            'partner_id': self.partner_id.id,
            'car_id': self.car_id.id,
            'mileage_on_arrival': self.car_id.mileage,
            'complaint': f"Appointment: {self.name} - {self.notes or 'No notes'}",
            'service_type_id': self.service_type_id.id,
        })
        self.reception_id = reception.id
        self.state = 'arrived'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'autofix.service.reception',
            'res_id': reception.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_no_show(self):
        self.write({'state': 'no_show'})

    @api.model
    def _cron_send_reminders(self):
        tomorrow = fields.Date.today() + timedelta(days=1)
        appointments = self.search([
            ('state', '=', 'confirmed'),
            ('appointment_date', '=', tomorrow),
            ('reminder_sent', '=', False),
        ])
        for appointment in appointments:
            if appointment.partner_id.email:
                template = self.env.ref('autofix.email_template_appointment_reminder', raise_if_not_found=False)
                if template:
                    template.send_mail(appointment.id, force_send=True)
                    appointment.reminder_sent = True