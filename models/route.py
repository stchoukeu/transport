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



class TransportRoute(models.Model):
    _name = 'transport.route'
    _inherit = ['mail.thread']
    _description = "Routes"
    _order = 'name,id' 
     
    name = fields.Char(
        string='Nom',
        readonly=True,
        compute='_compute_name',
        store= True,
    )
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
    )  
    
    depart_id = fields.Many2one(
        string='Départ',
        comodel_name='transport.endroit',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Place de départ pour le transport.',
    )
    arrivee_id = fields.Many2one(
        string='Arrivée',
        comodel_name='transport.endroit',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Place d\'arrivée.',
    ) 
    fraisroute = fields.Float(
        string='Montant Frais de route', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Montant frais de route',
    )

    distance = fields.Float(
        string='Distance(en Km)', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Distance(en kilomètre)',
    )
    vitesse = fields.Float(
        string='Vitesse moyenne(Km/h)', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=60,
        help='Vitesse moyenne(en Km/h)',
    )
    route_product_ids = fields.One2many(
        comodel_name='transport.route.product', 
        inverse_name='route_id', 
        string='Liste des prix de transport des produits', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    ) 
    endroit_route_ids = fields.One2many(
        comodel_name='transport.endroit.route', 
        inverse_name='route_id', 
        string='Places situées sur la route', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    ) 
    peage_route_ids = fields.One2many(
        comodel_name='transport.peage.route', 
        inverse_name='route_id', 
        string='Péages situées sur la route', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    observation = fields.Text(
        string='Observation', 
        readonly=False,
        states={'draft': [('readonly', False)]},
        help='Observation',
    )

    @api.model
    def _default_name(self):
        depart=''
        arrivee=''
        for record in self:
            depart=record.depart_id.name
            arrivee=record.arrivee_id.name
        return "%s->%s" % (depart,arrivee)  
    
    @api.multi
    @api.depends('depart_id', 'arrivee_id')
    def _compute_name(self):
        for record in self:
            depart=record.depart_id.name
            arrivee=record.arrivee_id.name
            record.name = "%s->%s" % (depart,arrivee)                  

    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        if values['depart_id']==values['arrivee_id']:
           raise UserError(_('La place de départ doit être différente de la place d\'arrivée')) 

        records = self.env['transport.route'].search(['&',('depart_id', '=', values['depart_id']),('arrivee_id', '=', values['arrivee_id'])])
        if records: 
                for record in records:
                    raise UserError(_('Cette route existe déjà numéro %s ' % (record.id)))  
                                 
        record = super(TransportRoute, self.with_context(mail_create_nolog=True)).create(values)
        return record 

    @api.multi
    def write(self,values):
        if 'depart_id' in values:
            if  values['depart_id']==values['arrivee_id']:
               raise UserError(_('La place de départ doit être différente de la place d\'arrivée')) 
            
            for record in self:
                if  record.depart_id!=values['depart_id']:
                    raise UserError(_('Vous ne pouvez modifier le debut et la fin de cette route'))  
                
                if  record.arrivee_id!=values['arrivee_id']:
                    raise UserError(_('Vous ne pouvez modifier le debut et la fin de cette route'))   
          
        record= super(TransportRoute, self.with_context(mail_create_nolog=True)).write(values)
        return record  
  
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportRoute, self).unlink()
                models.Model.unlink(self)
            else:
                raise UserError(_('Vous pouvez seulement supprimer les enregistrements qui sont soit annulés, soit à l\'état brouillon'))
                #raise Warning(_('You can only delete draft or cancel record'))
    @api.multi
    def bouton_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            for route_product in record.route_product_ids:
                route_product.bouton_draft() 
            for endroit_route in record.endroit_route_ids:
                endroit_route.bouton_draft()  
            for peage_route in record.peage_route_ids:
                peage_route.bouton_draft()  
    @api.multi
    def bouton_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
            for route_product in record.route_product_ids:
                route_product.bouton_cancel() 
            for endroit_route in record.endroit_route_ids:
                endroit_route.bouton_cancel() 
            for peage_route in record.peage_route_ids:
                peage_route.bouton_cancel()             
                                
                                
    @api.multi
    def bouton_confirm(self):
        for record in self:
            record.write({'state': 'confirm'})
            for route_product in record.route_product_ids:
                route_product.bouton_confirm()
            for endroit_route in record.endroit_route_ids:
                endroit_route.bouton_confirm()   
            for peage_route in record.peage_route_ids:
                peage_route.bouton_confirm()                  