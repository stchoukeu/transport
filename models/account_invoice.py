# -*- coding: utf-8 -*-
# Copyright 2017 TCHOUKEU Simplice Aimé
# Copyright 2017 Toolter Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, expression
from openerp import api, fields, models, _
from openerp.tools import float_is_zero, float_compare
from openerp.tools.misc import formatLang
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.exceptions import UserError, RedirectWarning, ValidationError



class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice']
     
    passager_id = fields.Many2one(
        string='Passager',
        comodel_name='transport.passager',
        required=False,
        help='Passager attaché à cette facture',
    ) 
    colis_id = fields.Many2one(
        string='Colis',
        comodel_name='transport.colis',
        required=False,
        help='Colis attaché à cette facture',
    ) 
    feuilleroute_id = fields.Many2one(
        string='Feuille de route',
        comodel_name='transport.feuille.route',
        required=False,
        help='Feuille de route attaché à cette facture',
    ) 
   