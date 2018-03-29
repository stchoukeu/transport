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



class TransportAgence(models.Model):
    _name = 'transport.agence'
    _inherit = ['mail.thread']
    _description = "Agence"
    _order = 'name' 
 
    name = fields.Char(
        string='Nom de l\'agence',
        required=True,
        readonly=False,
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
             " * Le statut 'Annulé' est utilisé quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n")
      
    endroit_id = fields.Many2one(
        string='Place',
        comodel_name='transport.endroit',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Localisation agence.',
    )
    state_id = fields.Many2one(
        'res.country.state',
        related="endroit_id.state_id",
        readonly=True,
        string="Région")
    country_id = fields.Many2one(
        'res.country',
        related="endroit_id.country_id",
        readonly=True,
        string="Pays")
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
            endroit=record.endroit_id.name
        return " %s[%s]" % (endroit,self.env['ir.sequence'].next_by_code(
            'transport.agence',
        ))      
   
    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportAgence, self.with_context(mail_create_nolog=True)).create(values)
        return record 
 
    @api.multi
    def write(self,values):
        record = super(TransportAgence, self.with_context(mail_create_nolog=True)).write(values)
        return record  
      
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportAgence, self).unlink()
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
                