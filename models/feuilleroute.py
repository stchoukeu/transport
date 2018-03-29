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



class TransportFeuilleRoute(models.Model):
    _name = 'transport.feuille.route'
    _inherit = ['mail.thread']
    _description = "Feuille de route"
    _order = 'id desc'
     
    name = fields.Char(
        string='Nom',
        required=True,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
    )
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
            ('planify', 'Planifié'),
            ('delivered', 'livré'),
            ('paid', 'Payé'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
             " * Le statut 'Planifié' est utilisé quand le transport du colis est planifié.\n"
             " * Le statut 'livré' est utilisé pour les colis déja livré au client  .\n"
             " * Le statut 'Payé' est utilisé quand la facture associée à cet enregistrement est déjà payée.\n"
    )  
      
    chauffeur_id = fields.Many2one(
        string='Chauffeur',
        comodel_name='transport.chauffeur',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Chauffeur ou conducteur du vehicule de transport.',
    )
    motoboy_id = fields.Many2one(
        string='Aide Chauffeur',
        comodel_name='transport.motoboy',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Aide chauffeur ou moto boy',
    )
    employee_chauffeur_id = fields.Many2one(
        string='Employé Chauffeur',
        comodel_name='hr.employee',
        required=False,
        index=True,
        readonly=True,
        store=True,
        related='chauffeur_id.employee_id', 
        help='Employé Chauffeur ou conducteur du vehicule de transport.',
    )
    employee_motoboy_id = fields.Many2one(
        string='Employé Aide Chauffeur',
        comodel_name='hr.employee',
        required=False,
        index=True,
        readonly=True,
        store=True,
        related='motoboy_id.employee_id', 
        help='Employé Aide chauffeur ou moto boy',
    )
    vehicule_id = fields.Many2one(
        string='Vehicule',
        comodel_name='transport.vehicule',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Véhicule de transport'
    )

    carburation_ids = fields.One2many(
        comodel_name='transport.carburation', 
        inverse_name='feuilleroute_id', 
        string='Carburations effectués', 
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )  
    voyage_ids = fields.One2many(
        comodel_name='transport.voyage', 
        inverse_name='feuilleroute_id', 
        string='Voyages planifiés', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )    
    fraisroute = fields.Float(
        string='Frais de route', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Frais de route',
    )
    mtpeages = fields.Float(
        string='Montant péages', 
        readonly=True,
        help='Montant péages',
    )
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Observation',
    )
    depart_prevu = fields.Datetime(
        string='Date départ prévu',
        required=True, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)]}, 
        copy=False, 
        default=fields.Datetime.now
    )
    depart_reel = fields.Datetime(
        string='Date départ réel', 
        required=False, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)],'planify': [('required', True),('readonly', False)]},
         copy=False
    )
    arrivee_prevu = fields.Datetime(
        string='Date Arrivée prévu', 
        required=False, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)],'planify': [('required', True),('readonly', False)]}, 
        copy=False
    )
    arrivee_reel = fields.Datetime(
        string='Date Arrivée réel', 
        required=False, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)],'delivered': [('required', True),('readonly', False)]}, 
        copy=False
    )  
    @api.model
    def _default_name(self):
        nom=''
        for record in self:
            nom=record.chauffeur_id.name
        return " %s[%s]" % (nom,self.env['ir.sequence'].next_by_code(
            'transport.feuille.route',
        ))  
                   

    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportFeuilleRoute, self.with_context(mail_create_nolog=True)).create(values)
        return record 

    @api.multi
    def write(self,values):
        for record in self:
            if len(record.voyage_ids)==0:
                raise UserError(_('Veuillez spécifier les voyages de la feuille de route'))
        record = super(TransportFeuilleRoute, self.with_context(mail_create_nolog=True)).write(values)
        return record
        
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportFeuilleRoute, self).unlink()
                models.Model.unlink(self)
            else:
                raise UserError(_('Vous pouvez seulement supprimer les enregistrements qui sont soit annulés, soit à l\'état brouillon'))
                #raise Warning(_('You can only delete draft or cancel record'))
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
                
    @api.multi
    def bouton_planify(self):
        for record in self:
            record.write({'state': 'planify'})
    @api.multi
    def bouton_delivered(self):
        for record in self:
            record.write({'state': 'delivered'})
                
    @api.multi
    def bouton_paid(self):
        for record in self:
            record.write({'state': 'paid'})
