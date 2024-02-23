import logging
from odoo import fields, models, api, _
from odoo.addons.helper import validator


class InheritCurrencyConversionRateCashIncentive(models.Model):
    _inherit = 'currency.conversion.rate'

    type = fields.Selection([
        ('01', 'Common'),
        ('02', 'Inter Bank'),
        ('03', 'Encashment'),
        ('04', 'OD Sight'),
    ], string='Type', copy=False, default='01')
    bank_id = fields.Many2one('res.bank', string='Bank', domain="[('is_cash_incentive_bank', '=', True)]")

    @api.constrains('date', 'currency_id')
    def _check_unique_constraint_date_currency(self):
        msg = 'Same currency "%s" of the Date and Type' % self.currency_id.name
        envobj = self.env['currency.conversion.rate']
        conditionlist = [('date', '=', self.date), ('currency_id', '=', self.currency_id.id), ('rate', '=', self.rate), ('type', '=', self.type)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)