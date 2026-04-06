from odoo import http

class AutoFixAPI(http.Controller):
    
    @http.route('/api/autofix/receptions', type='json', auth='public', methods=['GET'])
    def get_receptions(self, state=None, date_from=None, date_to=None, **kwargs):
        domain = []
        if state:
            domain.append(('state', '=', state))
        if date_from:
            domain.append(('date_received', '>=', date_from))
        if date_to:
            domain.append(('date_received', '<=', date_to))
        
        receptions = http.request.env['autofix.service.reception'].search(domain, limit=100)
        return [{
            'id': r.id,
            'name': r.name,
            'partner_id': r.partner_id.name,
            'car_id': r.car_id.name,
            'state': r.state,
            'date_received': str(r.date_received),
            'total_cost': r.total_cost,
        } for r in receptions]

    @http.route('/api/autofix/receptions/<int:reception_id>', type='json', auth='public', methods=['GET'])
    def get_reception(self, reception_id, **kwargs):
        reception = http.request.env['autofix.service.reception'].browse(reception_id)
        if not reception.exists():
            return {'error': 'Reception not found'}
        
        work_orders = [{
            'id': wo.id,
            'name': wo.name,
            'description': wo.description,
            'state': wo.state,
            'labor_cost': wo.labor_cost,
            'total_cost': wo.total_cost,
        } for wo in reception.work_order_ids]
        
        return {
            'id': reception.id,
            'name': reception.name,
            'partner_id': reception.partner_id.name,
            'car_id': reception.car_id.name,
            'state': reception.state,
            'date_received': str(reception.date_received),
            'total_cost': reception.total_cost,
            'work_orders': work_orders,
        }

    @http.route('/api/autofix/work-orders', type='json', auth='public', methods=['GET'])
    def get_work_orders(self, state=None, **kwargs):
        domain = []
        if state:
            domain.append(('state', '=', state))
        
        work_orders = http.request.env['autofix.work.order'].search(domain, limit=100)
        return [{
            'id': wo.id,
            'name': wo.name,
            'reception_id': wo.reception_id.name,
            'employee_id': wo.employee_id.name,
            'state': wo.state,
            'total_cost': wo.total_cost,
        } for wo in work_orders]

    @http.route('/api/autofix/cars', type='json', auth='public', methods=['GET'])
    def get_cars(self, **kwargs):
        cars = http.request.env['autofix.car'].search([], limit=100)
        return [{
            'id': c.id,
            'name': c.name,
            'brand_id': c.brand_id.name,
            'model_id': c.model_id.name,
            'year': c.year,
            'partner_id': c.partner_id.name,
        } for c in cars]

    @http.route('/api/autofix/dashboard', type='json', auth='public', methods=['GET'])
    def get_dashboard(self, **kwargs):
        data = http.request.env['autofix.service.reception'].get_dashboard_data()
        return data