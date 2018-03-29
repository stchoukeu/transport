# -*- coding: utf-8 -*-
import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, expression
from openerp import api, fields, models, _
from openerp.tools import float_is_zero, float_compare,float_round
from openerp.tools.misc import formatLang
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.exceptions import UserError, RedirectWarning, ValidationError



class TransportEndroitRoute(models.Model):
    _name = 'transport.endroit.route'
    #_inherit = ['mail.thread']
    _description = "Places de la Route"
    _order = 'route_id,ordre' 
    
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
    ) 
    route_id = fields.Many2one(
        string='Route',
        comodel_name='transport.route',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Route du colis.',
    )
    endroit_id = fields.Many2one(
        string='Place',
        comodel_name='transport.endroit',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Place de départ pour le transport.',
    )    
    
    ordre = fields.Integer(
        string="Ordre",
        default=10,
         help="Ordre d'arrivée depuis le point de debut et permettant de placer les points sur la route",
    )
    state_id = fields.Many2one(
        'res.country.state',
        related="endroit_id.state_id",
        readonly=True,
        string="Région",
    )
    country_id = fields.Many2one(
        'res.country',
        related="endroit_id.country_id",
        readonly=True,
        string="Pays",
    )
    
    _sql_constraints = [
            ('identification_uniq', 'unique (route_id,endroit_id)', "La route doit être unique pour une place donnée  !"),
            ('identification_uniq', 'unique (route_id,ordre)', "Cet ordre est déja appliqué à la route  !"),
    ]

    @api.multi
    def bouton_draft(self):
        for record in self:
            record.write({'state': 'draft'}) 

    @api.multi
    def bouton_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
    @api.multi
    def bouton_confirm(self):
        for record in self:
            record.write({'state': 'confirm'})
                
  