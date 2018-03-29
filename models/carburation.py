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



class TransportCarburation(models.Model):
    _name = 'transport.carburation'
    _inherit = ['mail.thread']
    _description = "Carburation"
    _order = 'id desc' 
    
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
            ('delivered', 'Delivré'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
             " * Le statut 'Delivré' est utilisé quand la facture est déjà payée et le service est délivré  .\n")
      
    #property_ids = fields.Many2many('mrp.property', 'sale_order_line_property_rel', 'order_id', 'property_id', 'Properties', readonly=True, states={'draft': [('readonly', False)]})
  
    feuilleroute_id = fields.Many2one(
        string='Feuille de Route',
        comodel_name='transport.feuille.route',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Feuille de Route .',
    )
    vehicule_id = fields.Many2one(
        string='Vehicule',
        comodel_name='transport.vehicule',
        readonly=True,
        required=False,
        store=True,
        related='feuilleroute_id.vehicule_id',
        help='Véhicule consommant le carburant',
    ) 
    chauffeur_id = fields.Many2one(
        string='Chauffeur',
        comodel_name='transport.chauffeur',
        required=False,
        index=True,
        readonly=True,
        store=True,
        related='feuilleroute_id.chauffeur_id',
        help='Chauffeur ou conducteur du vehicule de transport.',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        readonly=True,
        string='Produit carburé',
        ondelete='set null',
        index=True,
        store=True,
        related='vehicule_id.product_id',         
    ) 
    uom_id = fields.Many2one(
        string='Unité de mésure',
        comodel_name='product.uom',
        required=True,
        index=True,
        readonly=True,
        related='vehicule_id.uom_id', 
        help='Véhicule de transport'
    )  
    qte_consomme = fields.Float(
        string='Quantité Consommée', 
        store=True, 
        readonly=False,
    )
    date_conso = fields.Datetime(string='Date consommation', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Petite Observation',
    )
            

    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportCarburation, self.with_context(mail_create_nolog=True)).create(values)
        return record 

 
    @api.multi
    def write(self,values):
        record = super(TransportCarburation, self.with_context(mail_create_nolog=True)).write(values)
        return record  
         
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportCarburation, self).unlink()
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
    def bouton_delivered(self):
        for record in self:
            record.write({'state': 'delivered'})
            
        