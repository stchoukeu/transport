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



class TransportColis(models.Model):
    _name = 'transport.colis'
    _inherit = ['mail.thread']
    _description = "Colis à transporter"
    _order = 'id desc'
     
    name = fields.Char(
        string='Nom du colis',
        required=False,
        readonly=False,
        select=True,
        states={'draft': [('readonly', False)]},
    )
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

    partner_id = fields.Many2one(
        string='Client',
        comodel_name='res.partner',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Client propriétaire du colis',
        domain=[('customer', '=', True)]
    ) 
    reference = fields.Char(
        string='Reference', 
        readonly=True,
        required=True,
        states={'draft': [('readonly', False)]},
        help='Réference du document colis demandant le transport (bon de livraison ou bon de transfert)',
    )
    
    route_id = fields.Many2one(
        string='Route',
        comodel_name='transport.route',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Route du colis.',
    )
    depart_id = fields.Many2one(
        string='Départ',
        comodel_name='transport.endroit',
        required=False,
        index=True,
        readonly=True,
        store=True,
        related='route_id.depart_id',
        states={'draft': [('readonly', False)]},
        help='Place de départ pour le transport.',
    )
    arrivee_id = fields.Many2one(
        string='Arrivée',
        comodel_name='transport.endroit',
        required=False,
        index=True,
        readonly=True,
        store=True,
        related='route_id.arrivee_id',
        states={'draft': [('readonly', False)]},
        help='Place d\'arrivée.',
    )
    voyage_id = fields.Many2one(
        string='Voyage',
        comodel_name='transport.voyage',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Voyage embarquant le colis',
        domain=[('state', '=', 'draft')]
    )
    invoice_id = fields.Many2one(
        string='Facture du colis',
        comodel_name='account.invoice',
        required=False,
        index=True,
        readonly=True,
        help='La facture liée à ce colis',
    )
    invoice_state = fields.Selection(
        string='Etat facture du colis', 
        store=False, 
        readonly=False,
        related='invoice_id.state',
    )
    colis_product_ids = fields.One2many(
        comodel_name='transport.colis.product', 
        inverse_name='colis_id', 
        string='Produits du Colis ', 
        readonly=True,
        required=True,
        states={'draft': [('readonly', False)]},
        #states={'draft': [('readonly', False)],'confirm': [('required', True),('readonly', False)]},
        copy=True
    )    
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Observation',
    )
    type = fields.Selection([
            ('bl','BL'),
            ('bt', 'BT'),
        ], string='Type de colis', index=True, readonly=True, default='bl', copy=False,
    states={'draft': [('readonly', False)]},                        
    help=" Document initiateur du colis.\n"
         " BL: Bon de Livraison.\n"
         " BT: Bon de transfert.\n"
    ) 
    mttransport = fields.Float(
        string='Montant', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Montant transport du colis',
    )
    depart_prevu = fields.Datetime(
        string='Date départ prévu',
        required=True, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)]}, 
        copy=False, 
        default=fields.Datetime.now
    )
    depart_reel = fields.Datetime(
        string='Date départ réel', 
        required=False, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)],'planify': [('required', True),('readonly', False)]},
         copy=False
    )
    arrivee_prevu = fields.Datetime(
        string='Date Arrivée prévu', 
        required=False, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)],'planify': [('required', True),('readonly', False)]}, 
        copy=False
    )
    arrivee_reel = fields.Datetime(
        string='Date Arrivée réel', 
        required=False, 
        readonly=True, 
        index=True, 
        states={'draft': [('readonly', False)],'delivered': [('required', True),('readonly', False)]}, 
        copy=False
    )
    @api.multi
    @api.onchange('colis_product_ids')
    def _change_montant(self):
        result=[]
        #raise UserError(_('Vous pouvez seulement supprimer'))
        for record in self:  
            
            montant=0       
            if record.id and (not record.route_id):
                raise UserError(_('Veuillez selectioner d\'abord la route '))  
            
            if record.route_id:
                for colis_product in record.colis_product_ids:
                    trouve=False    
                    for route_product in record.route_id.route_product_ids:
                        if colis_product.product_id == route_product.product_id:
                            trouve=True
                            montant=montant+route_product.prixu_transport*colis_product.qtea_depart_prevu    
                    if not trouve:
                        raise UserError(_("Veuillez spécifier d'abord le prix de transport du produit %s sur la route %s ") % (colis_product.product_id.name,record.route_id.name))
      
            record.mttransport=montant
            result.append((record.id,montant) )
        return result;
    
    @api.model
    def _default_name(self):
        nom=''
        for record in self:
            endroit=record.reference
        return " %s[%s]" % (nom,self.env['ir.sequence'].next_by_code(
            'transport.colis',
        ))  
                   
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            display_name = "%s" % (record.reference)
            if  record.partner_id:
                display_name = "%s[%s]" % (record.reference,record.partner_id.name)
                if  record.route_id:
                    display_name = "%s[%s][%s]" % (record.reference,record.partner_id.name, record.route_id.name)

            result.append((record.id,display_name) )
        return result   
    
    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportColis, self.with_context(mail_create_nolog=True)).create(values)
        return record 
    
    @api.multi
    def write(self,values):
        #for record in self:
        #    if len(record.colis_product_ids)==0 and record.state=='draft':
        #        raise UserError(_('Veuillez spécifier les produits du colis à transporter'))
        record = super(TransportColis, self.with_context(mail_create_nolog=True)).write(values)
        return record  
         
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportColis, self).unlink()
                models.Model.unlink(self)
            else:
                raise UserError(_('Vous pouvez seulement supprimer les enregistrements qui sont soit annulés, soit à l\'état brouillon'))
                #raise Warning(_('You can only delete draft or cancel record'))
    @api.multi
    def bouton_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            for colis_produc in record.colis_product_ids:
                colis_produc.write({'state': 'draft'}) 
    @api.multi
    def bouton_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
            for colis_produc in record.colis_product_ids:
                colis_produc.write({'state': 'cancel'}) 
    @api.multi
    def bouton_confirm(self):
        for record in self:
            record.write({'state': 'confirm'})
            for colis_produc in record.colis_product_ids:
                colis_produc.write({'state': 'confirm'}) 
                
    @api.multi
    def bouton_planify(self):
        for record in self:
            record.write({'state': 'planify'})
            for colis_produc in record.colis_product_ids:
                colis_produc.write({'state': 'planify'}) 
    @api.multi
    def bouton_delivered(self):
        for record in self:
            record.write({'state': 'delivered'})
            for colis_produc in record.colis_product_ids:
                colis_produc.write({'state': 'delivered'}) 
                
    @api.multi
    def bouton_paid(self):
        for record in self:
            record.write({'state': 'paid'})
            for colis_produc in record.colis_product_ids:
                colis_produc.write({'state': 'paid'}) 


                
    @api.multi
    def bouton_confirm2(self):
                #preparing invoice
        for colis in self:
            self.ensure_one()
            journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
            if not journal_id:
                raise osv.except_osv(_('Attention!!'),_('Please define an accounting sale journal for this company.'))
            if not colis.product_id.property_account_income_id and not colis.product_id.categ_id.property_account_income_categ_id:
                raise osv.except_osv(_('Attention!!'),_('Please specify the revenue account in the accounting tab of this Medical act or product(service).'))  
                #colis.write({'end_date':fields.Date.context_today(self)}) 
                                   
            invoice_vals = {
                'name': colis.patient_id.partner_id.name,
                'colis_id': colis.id,
                'physician_id': colis.physician_id.id,
                'origin':  'Hospitalization -> #%s' % (colis.id),
                'type': 'out_invoice',
                'account_id': colis.patient_id.partner_id.property_account_receivable_id.id,
                'partner_id': colis.patient_id.partner_id.id,
                'journal_id': journal_id,
                'currency_id': colis.product_id.currency_id.id,
                'comment': '------------- ',
                'payment_term_id': colis.patient_id.partner_id.property_payment_term_id.id,
                'fiscal_position_id': colis.patient_id.partner_id.property_account_position_id.id ,
                'company_id': colis.patient_id.partner_id.company_id.id,
                'user_id': colis.create_uid.id,
                'team_id': colis.create_uid.team_id.id
            }
           
            invoice=self.env['account.invoice'].create(invoice_vals)
            
            #raise osv.except_osv(_('INVOICE %s' % (invoice.id)),_(' Is it the true?.'))
            #invoice= self.env['account.invoice'].browse(invoice.id) 
            property_account_income_id=False
            if colis.product_id.property_account_income_id:
                property_account_income_id= colis.product_id.property_account_income_id.id
            else:
                property_account_income_id= colis.product_id.categ_id.property_account_income_categ_id.id
            
            invoice_line_vals = { 
                'name': colis.product_id.name,
                'origin': 'INV: %s => %s' % (invoice.id,colis.patient_id.partner_id.name),
                'sequence': 1,
                'invoice_id': invoice.id,
                'uom_id': colis.product_id.uom_id.id,
                'product_id': colis.product_id.id,
                'account_id': property_account_income_id,
                'price_unit': colis.montant_untaxed, #Envisager d'appeler plutot la fonction qui renvoie le prix de la liste des prix (self.lit_id.categorie_id.product_id.list_price,) 
                'price_subtotal': colis.montant_untaxed,
                'price_subtotal_signed': colis.montant_untaxed,
                'quantity': 1,
                'discount': 0,
                'company_id': colis.patient_id.partner_id.company_id.id,
                'partner_id': colis.patient_id.partner_id.id,
                'currency_id': colis.product_id.currency_id.id,
                'company_currency_id': colis.product_id.currency_id.id,
                #'invoice_line_tax_ids':
                'account_analytic_id': False
            } 
            invoice_line=self.env['account.invoice.line'].create(invoice_line_vals)
            #raise osv.except_osv(_('INVOICE %s' % (invoice.id)),_(' Is it the true?.'))
            #invoice_line= self.env['account.invoice.line'].browse(ids_invoice_line[0])
            invoice_line._set_taxes();
            invoice_line._compute_price();
            self.env['account.invoice.line'].write(invoice_line)
            
            invoice._onchange_invoice_line_ids();
            invoice._compute_amount();
            vals = { 
                    'tax_line_ids': invoice.tax_line_ids,
                    'amount_untaxed': invoice.amount_untaxed,
                    'amount_tax': invoice.amount_tax,
                    'amount_total': invoice.amount_total,
                    'amount_total_company_signed':invoice.amount_total_company_signed,
                    'amount_total_signed': invoice.amount_total_signed,
                    'amount_untaxed_signed': invoice.amount_untaxed_signed,
                }             
            invoice.write(vals)
            
            #invoice.invoice_validate()
            #invoice.write(invoice)
            #invoice.post() 
            #invoice_line.post()
          
            #raise osv.except_osv(_('INVOICE %s' % (invoice.id)),_(' Is it the true....?.'))
            colis.write({'state': 'confirm','invoice_id':invoice.id})  
            
            if not colis.physician_id.employee_id:
                # Le practicien est quelcun de l'exterieur. Si la r�gle est d�fini alors on g�nere la facture d'achat de service pour ce dernier
                if not colis.product_id.property_account_expense_id and not colis.product_id.categ_id.property_account_expense_categ_id:
                    raise osv.except_osv(_('Attention!!'),_('Please specify the expense account in the accounting tab of this Medical act or product(service).'))
                
                    #colis.write({'end_date':fields.Date.context_today(self)}) 
                montant_achat=colis.montant_untaxed
                recs = self.env['physician.payment.term'].search(['&',('product_id', '=', colis.product_id.id),('physician_id', '=', colis.physician_id.id)])
                if recs: 
                    for term in recs:
                        montant_achat=montant_achat*term.percent_phisician                          
                    invoice_vals = {
                        'name': colis.physician_id.partner_id.name,
                        'colis_id': colis.id,
                        'physician_id': colis.physician_id.id,
                        'origin':  'Medical Act -> #%s' % (colis.id),
                        'type': 'in_invoice',
                        'account_id': colis.physician_id.partner_id.property_account_payable_id.id,
                        'partner_id': colis.physician_id.partner_id.id,
                        'journal_id': journal_id,
                        'currency_id': colis.product_id.currency_id.id,
                        'comment': '------------- ',
                        'payment_term_id': colis.physician_id.partner_id.property_supplier_payment_term_id.id,
                        'fiscal_position_id': colis.physician_id.partner_id.property_account_position_id.id ,
                        'company_id': colis.physician_id.partner_id.company_id.id,
                        'user_id': colis.create_uid.id,
                        'team_id': colis.create_uid.team_id.id
                    }
                   
                    invoice=self.env['account.invoice'].create(invoice_vals)
                    
                    #raise osv.except_osv(_('INVOICE %s' % (invoice.id)),_(' Is it the true?.'))
                    #invoice= self.env['account.invoice'].browse(invoice.id) 
                    property_account_expense_id=False
                    if colis.product_id.property_account_income_id:
                        property_account_expense_id= colis.product_id.property_account_expense_id.id
                    else:
                        property_account_expense_id= colis.product_id.categ_id.property_account_expense_categ_id.id
                  
                    invoice_line_vals = { 
                        'name': colis.product_id.name,
                        'origin': 'INV: %s => %s' % (invoice.id,colis.patient_id.partner_id.name),
                        'sequence': 1,
                        'invoice_id': invoice.id,
                        'uom_id': colis.product_id.uom_id.id,
                        'product_id': colis.product_id.id,
                        'account_id': property_account_expense_id,
                        'price_unit': montant_achat, #Envisager d'appeler plutot la fonction qui renvoie le prix de la liste des prix (self.lit_id.categorie_id.product_id.list_price,) 
                        'price_subtotal': montant_achat,
                        'price_subtotal_signed': montant_achat,
                        'quantity': 1,
                        'discount': 0,
                        'company_id': colis.physician_id.partner_id.company_id.id,
                        'partner_id': colis.physician_id.partner_id.id,
                        'currency_id': colis.product_id.currency_id.id,
                        'company_currency_id': colis.product_id.currency_id.id,
                        #'invoice_line_tax_ids':
                        'account_analytic_id': False
                    } 
                    invoice_line=self.env['account.invoice.line'].create(invoice_line_vals)
                    #raise osv.except_osv(_('INVOICE %s' % (invoice.id)),_(' Is it the true?.'))
                    #invoice_line= self.env['account.invoice.line'].browse(ids_invoice_line[0])
                    invoice_line._set_taxes();
                    invoice_line._compute_price();
                    self.env['account.invoice.line'].write(invoice_line)
                    
                    invoice._onchange_invoice_line_ids();
                    invoice._compute_amount();
                    vals = { 
                            'tax_line_ids': invoice.tax_line_ids,
                            'amount_untaxed': invoice.amount_untaxed,
                            'amount_tax': invoice.amount_tax,
                            'amount_total': invoice.amount_total,
                            'amount_total_company_signed':invoice.amount_total_company_signed,
                            'amount_total_signed': invoice.amount_total_signed,
                            'amount_untaxed_signed': invoice.amount_untaxed_signed,
                        }             
                    invoice.write(vals)  
                    colis.write({'supplier_invoice_id':invoice.id})              
