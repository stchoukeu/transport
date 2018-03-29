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



class TransportPassager(models.Model):
    _name = 'transport.passager'
    _inherit = ['mail.thread']
    _description = "Passager"
    _order = 'id desc' 
 
    state = fields.Selection([
            ('draft','Brouillon'),
            ('cancel', 'Annulé'),
            ('confirm', 'Confirmé'),
            ('paid', 'Payé'),
            ('delivered', 'Delivré'),
        ], string='Status', index=True, readonly=True, default='draft', copy=False,
        help=" * Le statut 'Brouillon' est utilisé lorsque l'enregistrement est crée mais non confirmé.\n"
             " * Le statut 'Annulé' est utilisé  quand un utilisateur annule l'enregistrement.\n"
             " * Le statut 'Confirmé' est utilisé quand un utilisateur confirme la création d'un enregistrement.\n"
             " * Le statut 'Payé' est utilisé quand la facture associée cet enregistrement est payée.\n"
             " * Le statut 'Delivré' est utilisé quand la facture est déjà payée et le service est délivré  .\n")
    
    depart_id = fields.Many2one(
        string='Départ',
        comodel_name='transport.endroit',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Place de départ du record.',
    )    
    destination_id = fields.Many2one(
        string='Destination',
        comodel_name='transport.endroit',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Destination du record.',
    ) 
    voyage_id = fields.Many2one(
        string='Voyage',
        comodel_name='transport.voyage',
        required=False,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Voyage embarquant le colis',
    )
    invoice_id = fields.Many2one(
        string='Facture',
        comodel_name='account.invoice',
        required=False,
        index=True,
        readonly=True,
        help='La facture liée é ce colis',
    )
    invoice_state = fields.Selection(
        string='Etat facture', 
        store=False, 
        readonly=False,
        related='invoice_id.state',
    )
    partner_id = fields.Many2one(
        string='Passager',
        comodel_name='res.partner',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Passager'
    )  
    mttransport = fields.Float(
        string='Montant transport', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Montant transport du colis',
    )
    observation = fields.Text(
        string='Observation', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Observation',
    ) 
     #def _onchange_pavillon_id(self):
     #   if self.pavillon_id:
     #       self.centrehospitalier_id.id = self.pavillon_id.centrehospitalier_id.id or False
            
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if not record.invoice_id:
                #name = "[{}] {}".format(record.id, record.name)
                name = "[%s] %s" % (record.create_date, record.partner_id.name)
                result.append((record.id,name) )
        return result

    @api.model
    def create(self,values):
        if 'state' in values:
            values['state'] = 'draft'
        record = super(TransportPassager, self.with_context(mail_create_nolog=True)).create(values)
        return record 
    
    @api.multi
    def write(self,values):
        record = super(TransportPassager, self.with_context(mail_create_nolog=True)).write(values)
        return record
     
    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'draft' or record.state=='cancel':
                #super(TransportPassager, self).unlink()
                models.Model.unlink(self)
            else:
                raise UserError(_('Vous pouvez seulement supprimer les enregistrements qui sont soit annulés, soit à l\'état brouillon'))
                #raise Warning(_('You can only delete draft or cancel record'))
 
    @api.multi
    def bouton_delivered(self):
        for record in self:
            invoice=record.invoice_id
            if not invoice or invoice.state!='paid':
                raise osv.except_osv(_('Auccun paiement détecté!!'),_("La facture attachée n'est pas encore payé. "))  
            record.write({'state': 'delivered'})
                                                           
    @api.multi
    def bouton_paid(self):
        for record in self:
            invoice=record.invoice_id
            if not invoice or invoice.state!='paid':
                raise osv.except_osv(_('Auccun paiement détecté!!'),_("La facture attachée n'est pas encore payé. ")) 
                #invoice.confirm_paid()
            record.write({'state': 'paid'})

    @api.multi
    def bouton_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
                
    @api.multi
    def bouton_confirm(self):
                #preparing invoice
        for record in self:
            self.ensure_one()
            journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
            if not journal_id:
                raise osv.except_osv(_('Attention!!'),_('Please define an accounting sale journal for this company.'))
            if not record.product_id.property_account_income_id and not record.product_id.categ_id.property_account_income_categ_id:
                raise osv.except_osv(_('Attention!!'),_('Please specify the revenue account in the accounting tab of this Medical act or product(service).'))  
                #record.write({'end_date':fields.Date.context_today(self)}) 
                                   
            invoice_vals = {
                'name': record.patient_id.partner_id.name,
                'record_id': record.id,
                'physician_id': record.physician_id.id,
                'origin':  'Hospitalization -> #%s' % (record.id),
                'type': 'out_invoice',
                'account_id': record.patient_id.partner_id.property_account_receivable_id.id,
                'partner_id': record.patient_id.partner_id.id,
                'journal_id': journal_id,
                'currency_id': record.product_id.currency_id.id,
                'comment': '------------- ',
                'payment_term_id': record.patient_id.partner_id.property_payment_term_id.id,
                'fiscal_position_id': record.patient_id.partner_id.property_account_position_id.id ,
                'company_id': record.patient_id.partner_id.company_id.id,
                'user_id': record.create_uid.id,
                'team_id': record.create_uid.team_id.id
            }
           
            invoice=self.env['account.invoice'].create(invoice_vals)
            
            #raise osv.except_osv(_('INVOICE %s' % (invoice.id)),_(' Is it the true?.'))
            #invoice= self.env['account.invoice'].browse(invoice.id) 
            property_account_income_id=False
            if record.product_id.property_account_income_id:
                property_account_income_id= record.product_id.property_account_income_id.id
            else:
                property_account_income_id= record.product_id.categ_id.property_account_income_categ_id.id
            
            invoice_line_vals = { 
                'name': record.product_id.name,
                'origin': 'INV: %s => %s' % (invoice.id,record.patient_id.partner_id.name),
                'sequence': 1,
                'invoice_id': invoice.id,
                'uom_id': record.product_id.uom_id.id,
                'product_id': record.product_id.id,
                'account_id': property_account_income_id,
                'price_unit': record.montant_untaxed, #Envisager d'appeler plutot la fonction qui renvoie le prix de la liste des prix (self.lit_id.categorie_id.product_id.list_price,) 
                'price_subtotal': record.montant_untaxed,
                'price_subtotal_signed': record.montant_untaxed,
                'quantity': 1,
                'discount': 0,
                'company_id': record.patient_id.partner_id.company_id.id,
                'partner_id': record.patient_id.partner_id.id,
                'currency_id': record.product_id.currency_id.id,
                'company_currency_id': record.product_id.currency_id.id,
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
            record.write({'state': 'confirm','invoice_id':invoice.id})  
            
            if not record.physician_id.employee_id:
                # Le practicien est quelcun de l'exterieur. Si la régle est défini alors on génere la facture d'achat de service pour ce dernier
                if not record.product_id.property_account_expense_id and not record.product_id.categ_id.property_account_expense_categ_id:
                    raise osv.except_osv(_('Attention!!'),_('Please specify the expense account in the accounting tab of this Medical act or product(service).'))
                
                    #record.write({'end_date':fields.Date.context_today(self)}) 
                montant_achat=record.montant_untaxed
                recs = self.env['physician.payment.term'].search(['&',('product_id', '=', record.product_id.id),('physician_id', '=', record.physician_id.id)])
                if recs: 
                    for term in recs:
                        montant_achat=montant_achat*term.percent_phisician                          
                    invoice_vals = {
                        'name': record.physician_id.partner_id.name,
                        'record_id': record.id,
                        'physician_id': record.physician_id.id,
                        'origin':  'Medical Act -> #%s' % (record.id),
                        'type': 'in_invoice',
                        'account_id': record.physician_id.partner_id.property_account_payable_id.id,
                        'partner_id': record.physician_id.partner_id.id,
                        'journal_id': journal_id,
                        'currency_id': record.product_id.currency_id.id,
                        'comment': '------------- ',
                        'payment_term_id': record.physician_id.partner_id.property_supplier_payment_term_id.id,
                        'fiscal_position_id': record.physician_id.partner_id.property_account_position_id.id ,
                        'company_id': record.physician_id.partner_id.company_id.id,
                        'user_id': record.create_uid.id,
                        'team_id': record.create_uid.team_id.id
                    }
                   
                    invoice=self.env['account.invoice'].create(invoice_vals)
                    
                    #raise osv.except_osv(_('INVOICE %s' % (invoice.id)),_(' Is it the true?.'))
                    #invoice= self.env['account.invoice'].browse(invoice.id) 
                    property_account_expense_id=False
                    if record.product_id.property_account_income_id:
                        property_account_expense_id= record.product_id.property_account_expense_id.id
                    else:
                        property_account_expense_id= record.product_id.categ_id.property_account_expense_categ_id.id
                  
                    invoice_line_vals = { 
                        'name': record.product_id.name,
                        'origin': 'INV: %s => %s' % (invoice.id,record.patient_id.partner_id.name),
                        'sequence': 1,
                        'invoice_id': invoice.id,
                        'uom_id': record.product_id.uom_id.id,
                        'product_id': record.product_id.id,
                        'account_id': property_account_expense_id,
                        'price_unit': montant_achat, #Envisager d'appeler plutot la fonction qui renvoie le prix de la liste des prix (self.lit_id.categorie_id.product_id.list_price,) 
                        'price_subtotal': montant_achat,
                        'price_subtotal_signed': montant_achat,
                        'quantity': 1,
                        'discount': 0,
                        'company_id': record.physician_id.partner_id.company_id.id,
                        'partner_id': record.physician_id.partner_id.id,
                        'currency_id': record.product_id.currency_id.id,
                        'company_currency_id': record.product_id.currency_id.id,
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
                    record.write({'supplier_invoice_id':invoice.id})              
