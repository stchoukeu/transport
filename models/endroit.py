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
from openerp.addons.base_geoengine import fields as geo_fields
from openerp.addons.base_geoengine import geo_model


class TransportEndroit(geo_model.GeoModel):
    _name = 'transport.endroit'
    _inherit = ['mail.thread']
    _description = "Endroit"
 
    name = fields.Char('Place', size=64, required=True, index=True) 
    complete_name = fields.Char(compute='_compute_complete_name')
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
        )
    
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        readonly=True,
        states={'draft': [('readonly', False)]},
        string='Nom Région'
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        related='state_id.country_id',
        readonly=True,
        string='Pays'
    )
    latitude = fields.Float(
        required=False, digits=(20, 10),
         readonly=True,
        states={'draft': [('readonly', False)]},
        help='GPS Latitude'
    )
    
    longitude = fields.Float(
        required=False, digits=(20, 10),
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='GPS Longitude'
    )
    #point = geo_fields.GeoPoint(
    #    string='Coordonées',
    #    store=True,
    #    compute='_compute_point',
    #    help='Coordonnée géospacial'
    #)
    
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Observation',
    )  
    @api.multi
    def get_coordinates(self):
        for rec in self:
            address = (rec.name + "," + rec.state_id.name + "," +
                       rec.country_id.name)
            google_url = (
                'http://maps.googleapis.com/maps/api/geocode/json?' +
                'address=' + address.encode('utf-8') + '&sensor=false')
            try:
                result = json.load(my_urllib.urlopen(google_url))
                if result['status'] == 'OK':
                    location = result['results'][0]['geometry']['location']
                    self.latitude = location['lat']
                    self.longitude = location['lng']
            except:
                raise UserError(_("Google Maps is not available."))

    @api.multi
    def open_in_google(self):
        for place in self:
            url = ("/transport/static/src/googlemaps/get_place_from_coords.html?" +
                   str(place.latitude) + ',' + str(place.longitude))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'nodestroy': True,
            'target': 'new'}

    @api.depends('state_id')
    def _compute_complete_name(self):
        for rec in self:
            if rec.state_id:
                rec.complete_name = rec.name + ', ' + rec.state_id.name
            else:
                rec.complete_name = rec.name
        

    @api.depends('latitude', 'longitude')
    def _compute_point(self):
        for rec in self:
            rec.point = geo_fields.GeoPoint.from_latlon(self.env.cr, rec.latitude, rec.longitude)
        

    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportEndroit, self.with_context(mail_create_nolog=True)).create(values)
        return record 

    @api.multi
    def write(self,values):
        record = super(TransportEndroit, self.with_context(mail_create_nolog=True)).write(values)
        return record
         
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportEndroit, self).unlink()
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
 