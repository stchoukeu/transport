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



class TransportMotoboy(models.Model):
    _name = 'transport.motoboy'
    _inherit = ['mail.thread']
    _description = "Aide chauffeur"
    _order = 'id desc' 
 
    name = fields.Char(
        required=False,
        readonly=True,
        translate=True,
        select=True,
        store=True,
        related='employee_id.name',
    )
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n")

    employee_id = fields.Many2one(
        string='Employé',
        comodel_name='hr.employee',
        required=True,
        index=True,
        readonly=False,
        help='L\'employé rattaché à ce chauffeur',
    )
    piece_id = fields.Many2one(
        string='Permit de conduire',
        comodel_name='transport.piece',
        required=False,
        index=True,
        readonly=False,
        help='Le permit de conduire de ce chauffeur',
    )
    contact_id = fields.Many2one(
        string='Contacts adresse',
        comodel_name='res.partner',
        required=False,
        index=True,
        readonly=True,
        store=True,
        related='employee_id.address_id',
        help='Lui ratacher une adresse',
    )
    permit_numero = fields.Char(
        string='Numéro permit',
        required=False,
        readonly=False,
        select=True,
        store=True,
        related='piece_id.reference',
        help='Numéro permit',
    )
    delivrance_date  = fields.Date(
        string='Date délivrance',
        required=False, 
        readonly=True, 
        index=True, 
        store=True,
        related='piece_id.delivrance_date',
    )
    expiration  = fields.Date(
        string='Date fin de validité',
        required=False, 
        readonly=True, 
        index=True, 
        store=True,
        related='piece_id.expiration',
    )
   
    days_to_expire = fields.Integer(
        string="Nombre de jour restant pour expiration",
        store=True,
        related='piece_id.days_to_expire',        
    )  

    permit_lieu = fields.Char(
        string='Lieu de délivrance Permit',
        required=False,
        readonly=True,
        select=True,
        store=True,
        related='piece_id.delivrance_lieu', 
    ) 
    voyage_ids = fields.One2many(
        comodel_name='transport.voyage', 
        inverse_name='motoboy_id', 
        string='Liste des voyages assistés', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )      
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Une observation sur le chauffeur?',
    )
    count_voyage_ids = fields.Integer(
        string='Voyages menés',
        compute='_compute_count_voyage_ids',
    )
     
    @api.multi
    def _compute_count_voyage_ids(self):
        for record in self:
            record.count_voyage_ids = len(record.voyage_ids)  
      
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

    _sql_constraints = [
            ('employee_uniq', 'unique (employee_id)', "Ce chauffeur existe déja !"),
    ]  
   
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if  record.employee_id:
                if record.employee_id.name:
                    name = "%s" % (record.employee_id.name)
                    result.append((record.id,name) )
                else:
                    if employee_id.address_id:
                        name = "%s" % (record.employee_id.address_id.name) 
                        result.append((record.id,name) )      
        return result          


    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportMotoboy, self.with_context(mail_create_nolog=True)).create(values)
        return record 

    @api.multi
    def write(self,values):
        record = super(TransportMotoboy, self.with_context(mail_create_nolog=True)).write(values)
        return record
         
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportMotoboy, self).unlink()
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