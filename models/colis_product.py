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



class TransportColisProduct(models.Model):
    _name = 'transport.colis.product'
    #_inherit = ['mail.thread']
    _description = "Produits du Colis"
 

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
 
    product_id = fields.Many2one(
        comodel_name='product.product',
        readonly=True,
        required=True,
        string='Produit',
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
        related='product_id.uom_id', 
        help='Véhicule de transport'
    ) 
    colis_id = fields.Many2one(
        string='Colis',
        comodel_name='transport.colis',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Colis',
    ) 
    qtea_depart_prevu = fields.Float(string='Quantité départ prévue', readonly=True,states={'draft': [('readonly', False)]})  
    qte15_depart_prevu= fields.Float(string='Quantité départ prévue(15° C)',  readonly=True,states={'draft': [('readonly', False)]})
    qtea_depart_chargee= fields.Float(string='Quantité départ chargée',  readonly=True,states={'planify': [('readonly', False)]})
    qte15_depart_chargee= fields.Float(string='Quantité départ chargée(15° C)',  readonly=True,states={'planify': [('readonly', False)]})
    qtea_livree= fields.Float(string='Quantité livrée',  readonly=True,states={'planify': [('readonly', False)]})
    qte15_livree= fields.Float(string='Quantité livrée(15° C)',  readonly=True,states={'planify': [('readonly', False)]})
    qte_perte = fields.Float(string='Quantité perdu',  readonly=True,states={'planify': [('readonly', False)]})
    prix_unitaire= fields.Float(string='Prix unitaire', readonly=True,states={'planify': [('readonly', False)]})
    mttransport= fields.Float(
        string='Montant Transport',  
        readonly=True,
        states={'draft': [('readonly', False)]}
    )                                                                                          

    _sql_constraints = [
            ('identification_uniq', 'unique (product_id,colis_id)', "Le produit existe déja !"),
    ]

    @api.multi
    @api.onchange('product_id','qtea_depart_prevu')
    def _change_montant(self):
        result=[]
        montant=0  
        for record in self: 
            if record.product_id: 
                if not record.colis_id.route_id:
                    raise UserError(_('Veuillez selectioner d\'abord la route ')) 
                trouve=False 
                for route_product in record.colis_id.route_id.route_product_ids:
                    if record.product_id == route_product.product_id:
                        trouve=True
                        montant=montant+route_product.prixu_transport*record.qtea_depart_prevu
                        record.prix_unitaire=route_product.prixu_transport
                        break    
                if not trouve:
                    raise UserError(_("Veuillez spécifier d'abord le prix de transport du produit %s sur la route %s ") % (record.product_id.name,record.colis_id.route_id.name))
                
            record.mttransport=montant      
            result.append((record.id,montant) )
        return result;

    @api.model
    def create(self,values):
        values['state'] = 'draft'
        record = super(TransportColisProduct, self).create(values)
        return record 
     
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportColisProduct, self).unlink()
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
