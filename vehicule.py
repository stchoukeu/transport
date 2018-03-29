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


class fleet_vehicle_log_fuel(models.Model):
    _name = 'fleet.vehicle.log.fuel'
    _inherit = ['fleet.vehicle.log.fuel']

    vehicule_id = fields.Many2one(
        string='Vehicule',
        comodel_name='transport.vehicule',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Véhicule de transport'
    )  
class fleet_vehicle_log_services(models.Model):
    _name = 'fleet.vehicle.log.services'
    _inherit = ['fleet.vehicle.log.services']

    vehicule_id = fields.Many2one(
        string='Vehicule',
        comodel_name='transport.vehicule',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Véhicule de transport'
    )  
class fleet_vehicle_log_contract(models.Model):
    _name = 'fleet.vehicle.log.contract'
    _inherit = ['fleet.vehicle.log.contract']

    vehicule_id = fields.Many2one(
        string='Vehicule',
        comodel_name='transport.vehicule',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Véhicule de transport'
    )  
class TransportVehicule(models.Model):
    _name = 'transport.vehicule'
    _description = "Vehicule"
    _order = 'name'
     
    def _vehicle_name_get_fnc(self):
        res = {}
        for record in self:
          record.name = record.model_id.brand_id.name + '/' + record.model_id.name + '/' + record.imatriculation
        return res

    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        if self.env.context is None:
            context = {}
        if self.env.context.get('xml_id'):
            context.pop('group_by', False)
            res = self.pool.get('ir.actions.act_window').for_xml_id(self.env.cr, self.env.uid ,'fleet', context['xml_id'], context=self.env.context)
            res['context'] = self.env.context
            res['context'].update({'default_vehicle_id': ids[0]})
            res['domain'] = [('vehicle_id','=', ids[0])]
            return res
        return False

    def act_show_log_cost(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        if self.env.context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(self.env.cr, self.env.uid ,'fleet','fleet_vehicle_costs_act', context=self.env.context)
        res['context'] = context
        res['context'].update({
            'default_vehicle_id': ids[0],
            'search_default_parent_false': True
        })
        res['domain'] = [('vehicle_id','=', ids[0])]
        return res

    def _get_odometer(self):
        res = dict.fromkeys(self.env.ids, 0)
        for record in self:
            ids = self.pool.get('fleet.vehicle.odometer').search(self.env.cr, self.env.uid, [('vehicle_id', '=', record.id)], limit=1, order='value desc')
            if len(ids) > 0:
                res[record.id] = self.pool.get('fleet.vehicle.odometer').browse(self.env.cr, self.env.uid, ids[0], context=context).value
        return res

    def _set_odometer(self):
        if value:
            date = datetime.now()
            data = {'value': value, 'date': date, 'vehicle_id': id}
            return self.pool.get('fleet.vehicle.odometer').create(self.env.cr, self.env.uid, data, context=self.env.context)

    def _search_get_overdue_contract_reminder(self):
        res = []
        for field, operator, value in self.env.args:
            assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
            if (operator == '=' and value == True) or (operator in ('<>', '!=') and value == False):
                search_operator = 'in'
            else:
                search_operator = 'not in'
            datetime.now()
            cr.execute('select cost.vehicle_id, count(contract.id) as contract_number FROM fleet_vehicle_cost cost left join fleet_vehicle_log_contract contract on contract.cost_id = cost.id WHERE contract.expiration_date is not null AND contract.expiration_date < %s AND contract.state IN (\'open\', \'toclose\') GROUP BY cost.vehicle_id', (today,))
            res_ids = [x[0] for x in self.env.cr.fetchall()]
            res.append(('id', search_operator, res_ids))
        return res

    def _search_contract_renewal_due_soon(self):
        res = []
        for field, operator, value in self.env.args:
            assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
            if (operator == '=' and value == True) or (operator in ('<>', '!=') and value == False):
                search_operator = 'in'
            else:
                search_operator = 'not in'
            today=datetime.now()
            datetime_today = datetime.datetime.strptime(today, tools.DEFAULT_SERVER_DATE_FORMAT)
            limit_date = str((datetime_today + relativedelta(days=+15)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
            cr.execute('select cost.vehicle_id, count(contract.id) as contract_number FROM fleet_vehicle_cost cost left join fleet_vehicle_log_contract contract on contract.cost_id = cost.id WHERE contract.expiration_date is not null AND contract.expiration_date > %s AND contract.expiration_date < %s AND contract.state IN (\'open\', \'toclose\') GROUP BY cost.vehicle_id', (today, limit_date))
            res_ids = [x[0] for x in self.env.cr.fetchall()]
            res.append(('id', search_operator, res_ids))
        return res

    def _get_contract_reminder_fnc(self):
        res= {}
        for record in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for element in record.log_contracts:
                if element.state in ('open', 'toclose') and element.expiration_date:
                    current_date_str = fields.date.context_today(self, self.env.cr, self.env.uid, context=self.env.context)
                    due_time_str = element.expiration_date
                    current_date = str_to_datetime(current_date_str)
                    due_time = str_to_datetime(due_time_str)
                    diff_time = (due_time-current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < 15 and diff_time >= 0:
                            due_soon = True;
                            total += 1
                    if overdue or due_soon:
                        ids = self.pool.get('fleet.vehicle.log.contract').search(self.env.cr,self.env.uid,[('vehicle_id', '=', record.id), ('state', 'in', ('open', 'toclose'))], limit=1, order='expiration_date asc')
                        if len(ids) > 0:
                            #we display only the name of the oldest overdue/due soon contract
                            name=(self.pool.get('fleet.vehicle.log.contract').browse(self.env.cr, self.env.uid, ids[0], context=context).cost_subtype_id.name)

            res[record.id] = {
                'contract_renewal_overdue': overdue,
                'contract_renewal_due_soon': due_soon,
                'contract_renewal_total': (total - 1), #we remove 1 from the real total for display purposes
                'contract_renewal_name': name,
            }
        return res

    def _get_default_state(self):
        try:
            model, model_id = self.pool.get('ir.model.data').get_object_reference(self.env.cr, self.env.uid, 'fleet', 'vehicle_state_active')
        except ValueError:
            model_id = False
        return model_id
    
    def _count_all(self):
        Odometer = self.pool['fleet.vehicle.odometer']
        LogFuel = self.pool['fleet.vehicle.log.fuel']
        LogService = self.pool['fleet.vehicle.log.services']
        LogContract = self.pool['fleet.vehicle.log.contract']
        Cost = self.pool['fleet.vehicle.cost']
        return {
            vehicle_id: {
                'odometer_count': Odometer.search_count(self.env.cr, self.env.uid, [('vehicle_id', '=', vehicle_id)], context=self.env.context),
                'fuel_logs_count': LogFuel.search_count(self.env.cr, self.env.uid, [('vehicle_id', '=', vehicle_id)], context=self.env.context),
                'service_count': LogService.search_count(self.env.cr, self.env.uid, [('vehicle_id', '=', vehicle_id)], context=self.env.context),
                'contract_count': LogContract.search_count(self.env.cr, self.env.uid, [('vehicle_id', '=', vehicle_id)], context=self.env.context),
                'cost_count': Cost.search_count(self.env.cr, self.env.uid, [('vehicle_id', '=', vehicle_id), ('parent_id', '=', False)], context=self.env.context)
            }
            for vehicle_id in ids
        }
   
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
    chauffeur_id = fields.Many2one('res.partner', string="Driver")
    employee_id = fields.Many2one(
        'hr.employee',
        string="Driver",
        domain=[('is_driver', '=', True)]
    )
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
    imatriculation = fields.Char(
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
    chauffeur_id = fields.Many2one(
        string='Chauffeur',
        comodel_name='transport.chauffeur',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Chauffeur ou conducteur du vehicule.',
    )
    model_id = fields.Many2one(
        string='Modèle',
        comodel_name='fleet.vehicle.model',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Modèle du vehicule.',
    )
    log_fuel = fields.One2many(
        comodel_name='fleet.vehicle.log.fuel', 
        inverse_name='vehicule_id', 
        string='Fuel Logs', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    log_services = fields.One2many(
        comodel_name='fleet.vehicle.log.services', 
        inverse_name='vehicule_id', 
        string='Services Logs', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    log_contracts = fields.One2many(
        comodel_name='fleet.vehicle.log.contract', 
        inverse_name='vehicule_id', 
        string='Contracts', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    fuel_type = fields.Selection([
            ('kilometers', 'Kilometers'),
            ('miles','Miles'),
        ], string='Odometer Unit', index=True, readonly=True, default='kilometers', copy=False,
        required=True,
        states={'draft': [('readonly', False)]},
        help=" Unit of the odometer \n"
    )
    fuel_type = fields.Selection([
            ('manual', 'Manual'),
            ('automatic', 'Automatic'),
        ], string='Transmission', index=True, readonly=True, default='gasoline', copy=False,
        states={'draft': [('readonly', False)]},
        help=" Transmission Used by the vehicle \n"
    ) 
    horsepower = fields.Integer(
        string='Horsepower',
        required=False,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Horsepower'
    )   
    horsepower_tax = fields.float(
        string='Horsepower Taxation',
        required=False,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Horsepower Taxation'
    ) 
    power = fields.Integer(
        string='Power',
        required=False,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Power in kW of the vehicle'
    ) 
    car_value = fields.float(
        string='Valeur Véhicule',
        required=False,
        readonly=True,
        translate=True,
        select=True,
        states={'draft': [('readonly', False)]},
        help='Valeur Véhicule'
    )       
    cost_count = fields.Integer(string='Costs', store=True, readonly=True, compute='_count_all', track_visibility='always')
    contract_count = fields.Integer(string='Contracts', store=True, readonly=True, compute='_count_all', track_visibility='always')
    service_count = fields.Integer(string='Services', store=True, readonly=True, compute='_count_all', track_visibility='always')
    fuel_logs_count = fields.Integer(string='Fuel Logs', store=True, readonly=True, compute='_count_all', track_visibility='always')
    odometer_count = fields.Float(string='Odometer', store=True, readonly=True, compute='_count_all', track_visibility='always')
    odometer = fields.Integer(string='Last Odometer', store=True, readonly=True, compute='_get_odometer',inverse='_set_odometer', track_visibility='always')
    
    contract_renewal_due_soon = fields.Integer(string='Has Contracts to renew', store=True, readonly=True, compute='_get_contract_reminder_fnc', track_visibility='always')
    contract_renewal_overdue = fields.Integer(string='Has Contracts Overdue', store=True, readonly=True, compute='_get_contract_reminder_fnc', track_visibility='always')
    contract_renewal_name = fields.Integer(string='Name of contract to renew soon', store=True, readonly=True, compute='_get_contract_reminder_fnc', track_visibility='always')
    service_count = fields.Integer(string='Total of contracts due or overdue minus one', store=True, readonly=True, compute='_get_contract_reminder_fnc', track_visibility='always')
    
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
                
                
    def on_change_model(self):
        if not model_id:
            return {}
        model = self.pool.get('fleet.vehicle.model').browse(self.env.cr, self.env.uid, model_id, context=self.env.context)
        return {
            'value': {
                'image_medium': model.image,
            }
        }

    def create(self,values):
        context = dict(self.env.context or {}, mail_create_nolog=True)
        values['state'] = 'draft'
        vehicle_id = super(TransportVehicule, self.with_context(mail_create_nolog=True)).create(values)
        vehicle = self.browse(vehicle_id)
        self.message_post(self.env.cr, self.env.uid, [vehicle_id], body=_('%s %s has been added to the fleet!') % (vehicle.model_id.name,vehicle.imatriculation), context=context)
        return vehicle_id

    def write(self,values):
        """
        This function write an entry in the openchatter whenever we change important information
        on the vehicle like the model, the drive, the state of the vehicle or its license plate
        """
        context = dict(self.env.context or {}, mail_create_nolog=True)
        for vehicle in self:
            changes = []
            if 'model_id' in vals and vehicle.model_id.id != vals['model_id']:
                value = self.pool.get('fleet.vehicle.model').browse(self.env.cr,self.env.uid,vals['model_id'],context=context).name
                oldmodel = vehicle.model_id.name or _('None')
                changes.append(_("Model: from '%s' to '%s'") %(oldmodel, value))
            if 'chauffeur_id' in vals and vehicle.chauffeur_id.id != vals['chauffeur_id']:
                value = self.pool.get('res.partner').browse(self.env.cr,self.env.uid,vals['chauffeur_id'],context=context).name
                olddriver = (vehicle.chauffeur_id.name) or _('None')
                changes.append(_("Driver: from '%s' to '%s'") %(olddriver, value))
            if 'state_id' in vals and vehicle.state_id.id != vals['state_id']:
                value = self.pool.get('fleet.vehicle.state').browse(self.env.cr,self.env.uid,vals['state_id'],context=context).name
                oldstate = vehicle.state_id.name or _('None')
                changes.append(_("State: from '%s' to '%s'") %(oldstate, value))
            if 'imatriculation' in vals and vehicle.imatriculation != vals['imatriculation']:
                old_imatriculation = vehicle.imatriculation or _('None')
                changes.append(_("License Plate: from '%s' to '%s'") %(old_imatriculation, vals['imatriculation']))

            if len(changes) > 0:
                self.message_post(self.env.cr, self.env.uid, [vehicle.id], body=", ".join(changes), context=context)

        vehicle_id = super(TransportVehicule,self.with_context(mail_create_nolog=True)).write(vals)
        return True    
     
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
    