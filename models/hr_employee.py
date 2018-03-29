# -*- coding: utf-8 -*-
# Copyright 2012, Israel Cruz Argil, Argil Consulting
# Copyright 2016, Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging
from datetime import datetime

from openerp import _, api, fields, models
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)
try:
    from sodapy import Socrata
except ImportError:
    _logger.debug('Cannot `import sodapy`.')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_driver = fields.Boolean(string="Est chauffeur",help='Est un Chauffeur')
    is_driver_helper = fields.Boolean(string="Est un aide chauffeur",help='Est un Chauffeur')
    advance_account_id = fields.Many2one(
        'account.account', 'Compte Avance')
    loan_account_id = fields.Many2one(
        'account.account', 'Compte de crédit')
    expense_negative_account_id = fields.Many2one(
        'account.account', 'Compte dépense Negative')
 
    income_percentage = fields.Float(string="Pourcentage revenu")
    
    voyage_chauffeur_ids = fields.One2many(
        comodel_name='transport.voyage', 
        inverse_name='employee_chauffeur_id', 
        string='Liste des voyages conduits', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    ) 
    voyage_motoboy_ids = fields.One2many(
        comodel_name='transport.voyage', 
        inverse_name='employee_motoboy_id', 
        string='Liste des voyages assistant', 
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True
    )
    @api.depends('license_expiration')
    def _compute_days_to_expire(self):
        for rec in self:
            if rec.license_expiration:
                date = datetime.strptime(rec.license_expiration, '%Y-%m-%d')
            else:
                date = datetime.now()
            now = datetime.now()
            delta = date - now
            rec.days_to_expire = delta.days if delta.days > 0 else 0
