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



class TransportVoyage(models.Model):
    _name = 'transport.voyage'
    _inherit = ['mail.thread']
    _description = "Voyage"
    _order = 'id desc'
     
    name = fields.Char(
        string='Nom',
        required=False,
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
             " * Le statut 'Payé' est utilisé quand la facture associée é cet enregistrement est déjé payée.\n"
    )   
    feuilleroute_id = fields.Many2one(
        string='Feuille de route',
        comodel_name='transport.feuille.route',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Feuille de route incluant ce voyage',
        domain=[('state', '=', 'draft')]
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
    agence_id = fields.Many2one(
        string='Agence',
        comodel_name='transport.agence',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Agence de transport'
    )
    route_id = fields.Many2one(
        string='Route',
        comodel_name='transport.route',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Route du colis.',
    )
    colis_ids = fields.One2many(
        comodel_name='transport.colis', 
        inverse_name='voyage_id', 
        string='Colis transportés', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )       
    fraisroute = fields.Float(
        string='Frais de route', 
        readonly=True,
        store='true',
        compute='_compute_montantetfrais',
        states={'draft': [('readonly', False)]},
        help='Frais de route',
    )
    mtpeages = fields.Float(
        string='Montant péages', 
        readonly=True,
        store='true',
        compute='_compute_montantetfrais',
        states={'draft': [('readonly', False)]},
        help='Montant péages',
    )
    mttransport = fields.Float(
        string='Montant', 
        readonly=True,
        store='true',
        compute='_compute_montantetfrais',
        states={'draft': [('readonly', False)]},
        help='Montant transport du colis',
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
    #domain=[('is_mecanician', '=', True),('is_electrician', '=', True)]  
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if  record.employee_chauffeur_id:
                if record.route_id.name:
                    name = "%s[%s][%s]" % (record.route_id.name,record.employee_chauffeur_id.name,record.id)
                    result.append((record.id,name) )     
        return result 
  
    @api.multi
    @api.onchange('colis_ids','route_id')      
    @api.depends('colis_ids', 'route_id')
    def _compute_montantetfrais(self):
        result=[]
        #fraisroute,mtpeages,mttransport
        for record in self:  
            montant=0
            for colis in record.colis_ids:
                montant=montant+colis.mttransport
            record.mttransport=montant
           
            montant=0
            for peage_route in record.route_id.peage_route_ids:
                montant=montant+peage_route.montant                
            record.mtpeages=montant
            record.fraisroute=record.route_id.fraisroute
                    

    def _change_montant_colis_ids(self):
        result=[]
        #fraisroute,mtpeages,mttransport
        for record in self:  
            montant=0
            for colis in record.colis_ids:
                montant=montant+colis.mttransport
            record.mttransport=montant
           
            montant=0
            for peage_route in record.route_id.peage_route_ids:
                montant=montant+peage_route.montant                
            record.mtpeages=montant
            record.fraisroute=record.route_id.fraisroute

    @api.multi
    @api.onchange('feuilleroute_id')
    def _change_feuilleroute_id(self):
        for record in self: 
            if not record.vehicule_id: 
                record.vehicule_id=record.feuilleroute_id.vehicule_id
    @api.multi
    @api.onchange('vehicule_id')
    def _change_feuilleroute_id(self):
        for record in self: 
            if not record.vehicule_id!=record.feuilleroute_id.vehicule_id: 
                record.feuilleroute_id=False

    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportVoyage, self.with_context(mail_create_nolog=True)).create(values)
        return record 
 
    
    @api.multi
    def write(self,values):
        for record in self:
            if len(record.colis_ids)==0:
                raise UserError(_('Veuillez spécifier le colis à transporter'))
        record = super(TransportVoyage, self.with_context(mail_create_nolog=True)).write(values)
        return record
        
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportVoyage, self).unlink()
                models.Model.unlink(self)
            else:
                raise UserError(_('Vous pouvez seulement supprimer les enregistrements qui sont soit annulés, soit à l\'état brouillon'))
                #raise Warning(_('You can only delete draft or cancel record'))
    @api.multi
    def bouton_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            for colis in record.colis_ids:
                colis.bouton_draft() 

    @api.multi
    def bouton_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
            for colis in record.colis_ids:
                colis.bouton_cancel()     
    @api.multi
    def bouton_confirm(self):
        for record in self:
            record.write({'state': 'confirm'})
            for colis in record.colis_ids:
                colis.bouton_confirm() 
                
    @api.multi
    def bouton_planify(self):
        for record in self:
            record.write({'state': 'planify'})
            for colis in record.colis_ids:
                colis.bouton_planify() 
    @api.multi
    def bouton_delivered(self):
        for record in self:
            record.write({'state': 'delivered'})
            for colis in record.colis_ids:
                colis.bouton_delivered()                 
    @api.multi
    def bouton_paid(self):
        for record in self:
            record.write({'state': 'paid'})
            for colis in record.colis_ids:
                colis.bouton_paid() 
