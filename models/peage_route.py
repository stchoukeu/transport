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



class TransportPeageRoute(models.Model):
    _name = 'transport.peage.route'
    #_inherit = ['mail.thread']
    _description = "Peages de la Route"
    _order = 'route_id' 
    
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
    peage_id = fields.Many2one(
        string='Péage',
        comodel_name='transport.peage',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Péage routier',
    )    
    
    montant = fields.Float(
        string="Coût du Péage",
        default=500,
        states={'draft': [('readonly', False)]},
        help="Montant du péage représentant le titre de passage",
    )
    
    _sql_constraints = [
            ('identification_uniq', 'unique(route_id,peage_id)', "Le péage doit être unique pour une route donnée!"),
    ]
    
    @api.multi
    @api.onchange('peage_id')
    def _change_montant(self):
        result=[]
        montant=0
        for record in self:
            montant=record.peage_id.montant
            record.montant=record.peage_id.montant
            result.append((record.id,montant) )
        return result;

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
                
  