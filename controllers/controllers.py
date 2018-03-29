# -*- coding: utf-8 -*-
from openerp import http

# class Tms(http.Controller):
#     @http.route('/tms/tms/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tms/tms/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tms.listing', {
#             'root': '/tms/tms',
#             'objects': http.request.env['tms.tms'].search([]),
#         })

#     @http.route('/tms/tms/objects/<model("tms.tms"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tms.object', {
#             'object': obj
#         })