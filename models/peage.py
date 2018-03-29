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



class TransportPeage(models.Model):
    _name = 'transport.peage'
    _inherit = ['mail.thread']
    _description = "Peages routier"
    _order = 'name' 
 
    name = fields.Char(
        string='Nom du point de péage',
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

        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
    )  
    
    montant = fields.Float(
        string='Montant Peage', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Montant du peage',
    )
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Observation',
    )
     
    @api.model
    def _default_name(self):
        endroit=''
        for record in self:
            endroit=record.name
        return " %s[%s]" % (endroit,self.env['ir.sequence'].next_by_code('transport.peage',))  
                   
    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportPeage, self.with_context(mail_create_nolog=True)).create(values)
        return record 
    
    @api.multi
    def write(self,values):
        record = super(TransportPeage, self.with_context(mail_create_nolog=True)).write(values)
        return record
          
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportPeage, self).unlink()
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
            