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



class TransportRouteProduct(models.Model):
    _name = 'transport.route.product'
    #_inherit = ['mail.thread']
    _description = "Régles des Prix de transport des produits"
 

    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
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
    route_id = fields.Many2one(
        string='Route',
        comodel_name='transport.route',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Route',
    ) 
    qte= fields.Float(string='Quantité', readonly=True,states={'draft': [('readonly', False)]},default=1)  
    montant= fields.Float(string='Montant Transport',  readonly=True,states={'draft': [('readonly', False)]})                                                                                          
    prixu_transport = fields.Float(
        string='Prix unitaire de transport ',
        compute='_compute_prixu_transport',
    )
    
    _sql_constraints = [
            ('identification_uniq', 'unique(product_id,route_id)', "Le produit existe déja !"),
    ]
    @api.onchange('qte','montant')
    @api.model
    def _compute_prixu_transport(self):
        result = []
        prix=0
        for record in self:
            prix=record.montant/record.qte
            record.prixu_transport=prix 
            result.append((record.id,prix) )
        return result;
            
    @api.model
    def create(self,values):
        values['state'] = 'draft'
        record = super(TransportRouteProduct, self).create(values)
        return record 
     
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportRouteProduct, self).unlink()
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
                


