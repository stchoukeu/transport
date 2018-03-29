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



class TransportPiece(models.Model):
    _name = 'transport.piece'
    _inherit = ['mail.thread']
    _description = "Pièces de véhicule"
    _order = 'id' 
 
    name = fields.Char(
        string='Nom de la pièce',
        required=True,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
    )
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulée'),
            ('confirm', 'Confirmée'),
            ('expired', 'Expirée'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
             " * Le statut 'Expirée' est utilisé quand la pièce est expirée.\n"
    )   
    vehicule_id = fields.Many2one(
        string='Vehicule',
        comodel_name='transport.vehicule',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Véhicule de transport'
    )
    chauffeur_id = fields.Many2one(
        string='Chauffeur',
        comodel_name='transport.chauffeur',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Chauffeur ou conducteur du vehicule de transport.',
    ) 
    employee_chauffeur_id = fields.Many2one(
        string='Employé Chauffeur',
        comodel_name='hr.employee',
        required=False,
        index=True,
        readonly=True,
        store=True,
        related='chauffeur_id.employee_id', 
        help='Employé Chauffeur titilaire de la piece ',
    )  
    reference = fields.Char(
        string='Reference(Numéro)', 
        readonly=True,
        required=True,
        states={'draft': [('readonly', False)]},
        help='Numéro de la pièce',
    )
    typepiece = fields.Selection([
            ('permit','Permit de conduire'),
            ('assurance', 'Assurance'),
            ('cartegrise', 'Carte grise'),
            ('licence', 'Licence'),
             ('autres', 'Autres'),
        ], string='Type de Pièce', index=True, readonly=True, default='assurance',                         
        states={'draft': [('readonly', False)]},copy=False,required=1,
        help=" * Le Permit de conduire .\n"
             " * L'Assurance .\n"
             " * La Carte grise .\n"
             " * La Licence .\n"
             " * Autres .\n"
    ) 
    categorie_type = fields.Char(
        string="Catégorie de la pièce",
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Catégorie de la pièce',           
    )
    delivrance_partner_id = fields.Many2one(
        string='Autorité de délivrance',
        comodel_name='res.partner',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Partenaire ayant délivré la pièce'
    )
    delivrance_lieu = fields.Char(
        string='Lieu de délivrance', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Lieu de délivrance',
    )
     
    delivrance_date  = fields.Date(string='Date délivrance', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    expiration = fields.Date(string='Date fin de validité', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    days_to_expire = fields.Integer(string="Nombre de jour restant pour expiration",compute='_compute_days_to_expire')  
   
    montant_piece = fields.Float(
        string='Coût de la pièce', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Montant de la pièce',
    )   
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Observation',
    )  
  
    @api.depends('expiration')
    def _compute_days_to_expire(self):
        for rec in self:
            if rec.expiration:
                date = datetime.strptime(rec.expiration, '%Y-%m-%d')
            else:
                date = datetime.now()
            now = datetime.now()
            delta = date - now
            rec.days_to_expire = delta.days if delta.days > 0 else 0
    
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            display_name = "%s[%s]" % (record.name,record.typepiece)
            if  record.reference:
                display_name = "%s[%s][%s]" % (record.name,record.reference,record.typepiece)


            result.append((record.id,display_name) )
        return result                     

    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportPiece, self.with_context(mail_create_nolog=True)).create(values)
        return record 
    
    @api.multi
    def write(self,values):
        record = super(TransportPiece, self.with_context(mail_create_nolog=True)).write(values)
        return record
   
    
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportPiece, self).unlink()
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
    def bouton_draft(self):
        for record in self:
            record.write({'state': 'draft'})