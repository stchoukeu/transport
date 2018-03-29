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



class TransportVehicule(models.Model):
    _name = 'transport.vehicule'
    _inherit = ['fleet.vehicle']
    _description = "Vehicule"
    #_order = 'name' 
    
    name = fields.Char(
        string='Nom du véhicule',
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
            ('exploitation', 'En exploitation'),
            ('panne', 'En panne'),
            ('reparation', 'En Reparation'),
            ('rebut', 'En Rebut'), 
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
             " * Le statut 'exploitation' est utilisé quand le véhicule est en exploitation.\n"
             " * Le statut 'panne' est utilisé quand le véhicule est en panne.\n"
             " * Le statut 'En Reparation' est utilisé quand le véhicule est en reparation.\n"
             " * Le statut 'En Rebut' est utilisé quand le véhicule est en rebut.\n"
    ) 
    feuilleroute_ids = fields.One2many(
        comodel_name='transport.feuille.route', 
        inverse_name='vehicule_id', 
        string='Feuilles de route', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    voyage_ids = fields.One2many(
        comodel_name='transport.voyage', 
        inverse_name='vehicule_id', 
        string='Voyages effectués', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    piece_ids = fields.One2many(
        comodel_name='transport.piece', 
        inverse_name='vehicule_id', 
        string='Liste des pièces', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    capacite = fields.Float(
        string='Capacité véhicule', 
        readonly=True,
        required=True,
        states={'draft': [('readonly', False)]},
        help='Capacité du véhicule',
    ) 
    typecarburant = fields.Selection([
            ('gazoil','Gazoil'),
            ('essence', 'Essence'),
            ('super', 'Super'),
            ('petrole', 'Pétrole'),
            ('autres', 'Autres'),
        ], string='Type de Carburant', index=True, readonly=True, default='gazoil',                         
        states={'draft': [('readonly', False)]},copy=False, required=1,
        help=" * Le Gazoil .\n"
             " * L'Essence .\n"
             " * Le super .\n"
             " * Le Pétrole .\n"
             " * Autres .\n"
    ) 
    product_id = fields.Many2one(
        comodel_name='product.product',
        readonly=True,
        required=True,
        string='Produit carburé',
        ondelete='set null',
        states={'draft': [('readonly', False)]},
        index=True
    )   
    uom_id = fields.Many2one(
        string='Unité de mésure',
        comodel_name='product.uom',
        required=True,
        index=True,
        readonly=True,
        store=True,
        related='product_id.uom_id', 
        help='Véhicule de transport'
    ) 
    acquisition_date = fields.Datetime(
        string='Date achat', 
        required=True, 
        readonly=True,
        index=True,
        states={'draft': [('readonly', False)]},
        copy=False, 
        default=fields.Datetime.now
    )
    year_model = fields.Char()
    serial_number = fields.Char()
    registration = fields.Char()
    fleet_type = fields.Selection(
        [('tractor', 'Motorized Unit'),
         ('trailer', 'Trailer'),
         ('dolly', 'Dolly'),
         ('other', 'Autre')],
        string='Unit Fleet Type')
     
    active = fields.Boolean(default=True)
    driver_id = fields.Many2one('res.partner', string="Driver")
    employee_id = fields.Many2one(
        'hr.employee',
        string="Driver",
        domain=[('is_driver', '=', True)])
    #expense_ids = fields.One2many('tms.expense', 'unit_id', string='Expenses')
    supplier_unit = fields.Boolean()  
    reference = fields.Text(
        string='Reference', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Reference',
    )
    installe_le = fields.Datetime(string='Installé le', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now, help='Date d\'installation')
    mise_en_service = fields.Date(string='Première Mise en service', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now, help='Date de premiere mise en service')
    expiration = fields.Date(string='Date de fin', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    duree_vie_usine = fields.Float(
        string='Durée de vie(en nbre de jour)', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Durée de vie à la sortie d\'usine',
        required=False
    )   
    days_to_expire = fields.Integer(string="Nombre de jour restant",compute='_compute_days_to_expire',help="Nombre de jour restant Pour expiration")  
   
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Observation',
    )  
    company_id = fields.Many2one(
        comodel_name='res.company',
        readonly=True,
        required=False,
        string='Entreprise',
        ondelete='set null',
        states={'draft': [('readonly', False)]},
        index=True
    )
    license_plate = fields.Char(
        string='Imatriculation',
        required=True,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='License plate number of the vehicle (ie: plate number for a car)'
    )
    vin_sn = fields.Char(
        string='Numéro chassit',
        required=True,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Unique number written on the vehicle motor (VIN/SN number)'
    )
    color = fields.Char(
        string='Couleur',
        required=False,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Couleur'
    )    
    location = fields.Char(
        string='Localisation',
        required=False,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Location of the vehicle (garage, ...)'
    )  
    seats = fields.Integer(
        string='Chaises',
        required=True,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Nombre de chaise'
    )
    doors = fields.Integer(
        string='Portes',
        required=True,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Nombre de Portes'
    )
    fuel_type = fields.Selection([
            ('gasoline', 'Gasoline'),
            ('diesel', 'Diesel'),
            ('electric', 'Electric'),
            ('hybrid', 'Hybrid'),
        ], string='Type carburant', index=True, readonly=True, default='gasoline', copy=False,
        states={'draft': [('readonly', False)]},
        help=" Fuel Used by the vehicle \n"
    )

    
    @api.depends('expiration','mise_en_service')
    def _compute_days_to_expire(self):
        for rec in self:
            if rec.expiration:
                date = datetime.strptime(rec.expiration, '%Y-%m-%d')
                mise_en_service= datetime.strptime(rec.mise_en_service, '%Y-%m-%d')
            else:
                date = datetime.now()
            now = datetime.now()
            delta = date - now
            delat_all=mise_en_service-date
            rec.days_to_expire = delta.days if delta.days > 0 else 0
            rec.duree_vie_usine=delat_all.days  if delat_all.days > 0 else 0               

    @api.model
    def create(self,values):
        values['state'] = 'draft'
            
        record = super(TransportVehicule, self.with_context(mail_create_nolog=True)).create(values)
        return record 
     
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportVehicule, self).unlink()
                models.Model.unlink(self)
            else:
                raise UserError(_('Vous pouvez seulement supprimer les enregistrements qui sont soit annulés, soit à l\'état brouillon'))
                #raise Warning(_('You can only delete draft or cancel record'))
    @api.multi
    def bouton_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
    @api.multi
    def bouton_confirm(self):
        for record in self:
            record.write({'state': 'confirm'})
    @api.multi
    def bouton_rebut(self):
        for record in self:
            record.write({'state': 'rebut'})
    @api.multi
    def bouton_reparation(self):
        for record in self:
            record.write({'state': 'reparation'})                
    @api.multi
    def bouton_panne(self):
        for record in self:
            record.write({'state': 'panne'})
    @api.multi
    def bouton_exploitation(self):
        for record in self:
            record.write({'state': 'exploitation'})
    