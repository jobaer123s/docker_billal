from odoo import exceptions,fields, models, _, api
from odoo.exceptions import UserError
from odoo.addons.helper import validator
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Many2one
from odoo.exceptions import AccessError
from datetime import datetime, timedelta


class EncashmentRateWizard(models.TransientModel):
    _name = "en.rate.wizard"

    swift_id = fields.Many2one('swift.message', string='SWIFT Message')
    partner_id = fields.Many2one('res.partner', 'Customer', related='swift_id.partner_id')

    currency_id = fields.Many2one("res.currency", string="Currency")
    date = fields.Date(string='SWIFT Date', required=True, default=fields.Date.context_today)
    bank_id = fields.Many2one('res.bank', string='SWIFT Bank', domain="[('is_cash_incentive_bank', '=', True)]")
    erq_bank_id = fields.Many2one('res.bank', string='ERQ Bank', domain="[('is_cash_incentive_bank', '=', True)]")

    invoice_amt = fields.Float(string='Invoice Amount (FC)', digits=(16, 2))
    swift_amount = fields.Float(string='Encashable SWIFT Amount (FC)', digits=(16, 2))
    swift_amt_bdt = fields.Float(string='Encashable Amount (BDT)', digits=(16, 2))
    encashment_charge = fields.Float(string='Bank Charge (FC)', digits=(16, 2), default=0)
    encashment_charge_bdt = fields.Float(string='Bank Charge (BDT)', digits=(16, 2))
    # swift_rate_bdt = fields.Float(string='SWIFT Rate (BDT)', digits=(16, 2), default=0)

    encashment_bank_id = fields.Many2one('res.bank', string='Encashment Bank', tracking=17, domain="[('is_cash_incentive_bank', '=', True)]")
    encashment_date = fields.Date(string='Encashment Date', default=fields.Date.context_today)

    encashment_rate = fields.Float(string='Encashment Rate (BDT)', digits=(16, 4))
    encashment_amount = fields.Float(string='Encashment Amount (BDT)', digits=(16, 2))
    difference_amnt_bdt = fields.Float(string='Foreign Exchange Gain/Loss (BDT)', digits=(16, 2))

    invoice_line_ids = fields.Many2many('cash.incentive.invoice', string='Invoices', tracking=18)

    #bank_charge = fields.Float(string='Bank Charge (FC)', digits=(16, 2))
    #other_charge = fields.Float(string='Other Charge (FC)', digits=(16, 2))

    remaining_swift_amount = fields.Float(string='Remaining SWIFT Amount (FC)', compute='_compute_remaining_amount', tracking=6)
    remaining_swift_amount_bdt = fields.Float(string='Remaining Encashment Amount (BDT)', tracking=6)

    is_erq_applicable = fields.Boolean(string='Is ERQ Applicable?',default=False)
    inter_bank_rate_bdt = fields.Float(string='Inter-Bank Rate (BDT)', digits=(16, 4))
    erq_percentage = fields.Float(string='ERQ (%)', digits=(16, 5))
    bdt_encashment_percentage = fields.Float(string='Encashment (%)', digits=(16, 5))
    erq_amount_fc = fields.Float(string='ERQ Amount (FC)', digits=(16, 2))
    fc_encashment_amount = fields.Float(string='Encashment Amount (FC) ', digits=(16, 2))
    erq_amount_bdt = fields.Float(string='ERQ Amount (BDT)', digits=(16, 2))
    bdt_encashment_amount = fields.Float(string='Encashment Amount (BDT) ', digits=(16, 2))
    total_erq_encashment_amount = fields.Float(string='ERQ and Encashment Total (BDT) ', digits=(16, 2))

    type = fields.Char()

    # invoice_line_ids = fields.One2many('journal.wizard.line', 'head_id', string='Invoices', tracking=18)

    invoice_ids = fields.One2many('en.rate.wizard.invoice', 'head_id', string='Invoices')
    erq_amount_fc_invoices = fields.Float(string='Invoices ERQ Amount (FC)', digits=(16, 2), compute='_compute_erq_amount_fc_invoices')

    @api.depends("invoice_ids")
    def _compute_erq_amount_fc_invoices(self):
        for row in self:
            erq_fc=0
            for rec in row.invoice_ids:
                erq_fc += rec.erq_fc
            row.erq_amount_fc_invoices=erq_fc

    @api.model
    def default_get(self, fields):
        res = super(EncashmentRateWizard, self).default_get(fields)
        # for global ------------

        multiple = self.env.context.get('multiple')
        encashment_date = datetime.today()

        currency_ids = []
        bank_ids = []
        if multiple == '1':
            swift_amount = 0
            swift_amt_bdt = 0
            encashment_charge = 0
            encashment_charge_bdt = 0

            active_ids = self.env.context.get('active_ids')
            all_inv = self.env['cash.incentive.invoice'].sudo().search([('swift_message_id', '=', active_ids)])
            swift_obj = None
            for data in active_ids:
                swift_obj = self.env['swift.message'].sudo().browse(data)


                if swift_obj.currency_id.id not in currency_ids:
                    currency_ids.append(swift_obj.currency_id.id)
                if swift_obj.bank_id.id not in bank_ids:
                    bank_ids.append(swift_obj.bank_id.id)

                swift_amount += swift_obj.swift_amt
                swift_amt_bdt += swift_obj.swift_amt_bdt
                encashment_charge += swift_obj.encashment_charge
                encashment_charge_bdt += swift_obj.encashment_charge_bdt

                if swift_obj.state != 'confirm':
                    raise AccessError(
                        _("Warning! %s SWIFT Message should be Confirm state." %(swift_obj.code))
                    )
            res['swift_amount'] = swift_amount
            res['swift_amt_bdt'] = swift_amt_bdt
            res['encashment_charge'] = encashment_charge
            res['encashment_charge_bdt'] = encashment_charge_bdt

            if len(currency_ids) > 1:
                raise AccessError(
                    _("Warning! Different Currency is not allowed.")
                )
            if len(bank_ids) > 1:
                raise AccessError(
                    _("Warning! Different Bank is not allowed.")
                )

            currency_id = currency_ids[0]
            res['currency_id'] = currency_id
            res['type'] = multiple

            bank_id = bank_ids[0]

            res['bank_id'] = bank_id
            res['encashment_bank_id'] = bank_id


            # ------------
            currency_rate_obj = self.env['currency.conversion.rate'].search(
                [('date', '<=', encashment_date), ('currency_id', '=', currency_id), ('bank_id', '=', bank_id),
                 ('type', '=', '03')],
                order='date DESC', limit=1)
            if currency_rate_obj:
                res['encashment_rate'] = currency_rate_obj.rate
            else:
                res['encashment_rate'] = 0

            # ----------
            currency_rate_obj2 = self.env['currency.conversion.rate'].search(
                [('date', '<=', encashment_date), ('currency_id', '=', currency_id), ('bank_id', '=', bank_id),
                 ('type', '=', '02')],
                order='date DESC', limit=1)
            if currency_rate_obj2:
                res['inter_bank_rate_bdt'] = currency_rate_obj2.rate
            else:
                res['inter_bank_rate_bdt'] = 0

        else:
            swift_id = self.env.context.get('swift_id')
            swift_id_obj = self.env['swift.message'].sudo().browse(swift_id)
            all_inv = self.env['cash.incentive.invoice'].sudo().search([('swift_message_id', '=', swift_id)])

            res['swift_id'] = swift_id
            res['invoice_amt'] = swift_id_obj.invoice_amt
            res['swift_amount'] = swift_id_obj.swift_amt
            res['swift_amt_bdt'] = swift_id_obj.swift_amt_bdt
            res['encashment_charge'] = swift_id_obj.encashment_charge
            res['encashment_charge_bdt'] = swift_id_obj.encashment_charge_bdt

            # res['swift_rate_bdt'] = swift_id_obj.swift_rate_bdt

            res['bank_id'] = swift_id_obj.bank_id.id
            res['encashment_bank_id'] = swift_id_obj.bank_id.id
            res['date'] = swift_id_obj.date

            currency_id = swift_id_obj.currency_id.id
            bank_id = swift_id_obj.bank_id.id

            #------------
            currency_rate_obj = self.env['currency.conversion.rate'].search(
                [('date', '<=', encashment_date), ('currency_id', '=', currency_id), ('bank_id', '=', bank_id), ('type', '=', '03')],
                order='date DESC', limit=1)
            if currency_rate_obj:
                res['encashment_rate'] = currency_rate_obj.rate
            else:
                res['encashment_rate'] = 0

            #----------
            currency_rate_obj2 = self.env['currency.conversion.rate'].search(
                [('date', '<=', encashment_date), ('currency_id', '=', currency_id), ('bank_id', '=', bank_id),
                 ('type', '=', '02')],
                order='date DESC', limit=1)
            if currency_rate_obj2:
                res['inter_bank_rate_bdt'] = currency_rate_obj2.rate
            else:
                res['inter_bank_rate_bdt'] = 0

            res['currency_id'] = currency_id

        all_inv_ids = [(0, 0, {'invoice_id': x.id, 'swift_fc': x.swift_amt, 'erq_fc': 0, 'encash_fc': x.swift_amt}) for x in all_inv]

        res['invoice_ids'] = all_inv_ids
        return res

    @api.onchange('erq_bank_id')
    def _onchange_erq_bank_id(self):
        if self.erq_bank_id:
            encashment_date = self.encashment_date
            currency_rate_obj = self.env['currency.conversion.rate'].search(
                [('date', '<=', encashment_date), ('currency_id', '=', self.currency_id.id), ('bank_id', '=', self.erq_bank_id.id),
                 ('type', '=', '02')],
                order='date DESC', limit=1)
            self.inter_bank_rate_bdt = currency_rate_obj.rate

    @api.onchange('encashment_bank_id','encashment_date')
    def onchange_encashment_bank_id_date(self):
        if self.currency_id and self.encashment_bank_id and self.encashment_date:
            for rec in self:
                currency_rate_obj = self.env['currency.conversion.rate'].search(
                    [('date', '<=', rec.encashment_date), ('bank_id', '=', rec.encashment_bank_id.id),
                     ('currency_id', '=', rec.currency_id.id),
                     ('type', '=', '03')], order='date DESC', limit=1)
                if currency_rate_obj:
                    rec.encashment_rate = currency_rate_obj.rate
                else:
                    rec.encashment_rate = 0
                # ----------
                currency_rate_obj2 = self.env['currency.conversion.rate'].search(
                    [('date', '<=', rec.encashment_date), ('bank_id', '=', rec.encashment_bank_id.id), ('currency_id', '=', rec.currency_id.id),
                     ('type', '=', '02')], order='date DESC', limit=1)
                if currency_rate_obj2:
                    rec.inter_bank_rate_bdt = currency_rate_obj2.rate
                else:
                    rec.inter_bank_rate_bdt = 0

    @api.depends("encashment_rate", "encashment_charge")
    def _compute_remaining_amount(self):
        for rec in self:
            total_amnt = 0
            # if rec.bank_charge:
            #     total_amnt += rec.bank_charge
            # if rec.encashment_charge:
            #     total_amnt += rec.encashment_charge
            # if rec.other_charge:
            #     total_amnt += rec.other_charge
            remaining_amnt = rec.swift_amount # - total_amnt

            rec.remaining_swift_amount = remaining_amnt
            rec.remaining_swift_amount_bdt = remaining_amnt * rec.encashment_rate

            #rec.encashment_charge_bdt = rec.encashment_charge * rec.swift_rate_bdt

    @api.onchange('is_erq_applicable')
    def onchange_is_erq_applicable(self):
        if self.is_erq_applicable == False:
            self.erq_amount_bdt = 0
            self.erq_percentage = 0
            self.bdt_encashment_percentage = 0
            self.bdt_encashment_amount = 0
            self.fc_encashment_amount = 0
            self.erq_amount_fc = 0
            self.total_erq_encashment_amount = 0

    @api.onchange('erq_percentage','inter_bank_rate_bdt','encashment_rate')
    def onchange_erq_percentage(self):
        if self.erq_percentage:
            limit_obj = self.env['erq.limit'].search([('date', '<=', self.date)], order='date DESC', limit=1)
            if limit_obj:
                print(limit_obj.limit)
                print(self.erq_percentage)
                if round(self.erq_percentage, 2) > limit_obj.limit:
                    raise UserError(_('ERQ Limit can not be Greater than Predefined Limit %s.') %limit_obj.limit)
                self.bdt_encashment_percentage = 100 - self.erq_percentage
            else:
                if self.erq_percentage > 100:
                    raise UserError(_('ERQ Limit can not be greater than 100.'))
                if self.erq_percentage < 0:
                    raise UserError(_('ERQ Limit can not be less than 0.'))
                self.bdt_encashment_percentage = 100 - self.erq_percentage

            erq_amount_fc = self.remaining_swift_amount / 100
            self.erq_amount_fc = round((self.erq_percentage * erq_amount_fc), 2) 
            self.fc_encashment_amount = round((self.bdt_encashment_percentage * erq_amount_fc), 2)

            self.erq_amount_bdt = round((self.erq_amount_fc * self.inter_bank_rate_bdt), 2)
            self.bdt_encashment_amount = round((self.fc_encashment_amount * self.encashment_rate), 2)
            self.total_erq_encashment_amount = self.erq_amount_bdt + self.bdt_encashment_amount

            self.onchange_encashment_rate()
    @api.onchange('erq_amount_fc')
    def onchange_erq_amount_fc(self):
        if self.erq_amount_fc:
            self.fc_encashment_amount = self.remaining_swift_amount - self.erq_amount_fc
            erq_percentage = 100 / self.remaining_swift_amount
            self.erq_percentage = self.erq_amount_fc * erq_percentage
            
            bdt_encashment_percentage = 100 / self.remaining_swift_amount
            self.bdt_encashment_percentage = self.fc_encashment_amount * bdt_encashment_percentage

    @api.onchange('encashment_rate', 'is_erq_applicable')
    def onchange_encashment_rate(self):
        if self.encashment_rate:
            if self.encashment_rate < 0:
                raise UserError(_('Rate can not be less than 0.'))

            encashment_amount = round((self.swift_amount * self.encashment_rate), 2)
            self.encashment_amount = encashment_amount

            if self.remaining_swift_amount:
                remaining_swift_amount_bdt = round((self.remaining_swift_amount * self.encashment_rate), 2)
                self.remaining_swift_amount_bdt = remaining_swift_amount_bdt

            if self.is_erq_applicable:
                self.difference_amnt_bdt = self.total_erq_encashment_amount - self.swift_amt_bdt
            else:
                self.difference_amnt_bdt = self.encashment_amount - self.swift_amt_bdt

            # if self.erq_amount_fc:
            #     erq_amount_bdt = round((self.erq_amount_fc * self.encashment_rate), 2)
            #     self.erq_amount_bdt = erq_amount_bdt
            #
            # if self.fc_encashment_amount:
            #     bdt_encashment_amount = round((self.fc_encashment_amount * self.encashment_rate), 2)
            #     self.bdt_encashment_amount = bdt_encashment_amount

    def js_python_method(self):
        pass

    def confirm_rate(self):
        if self.is_erq_applicable:
            if self.erq_amount_fc != self.erq_amount_fc_invoices:
                raise exceptions.ValidationError("ERQ Amount (FC) and Invoices ERQ Amount (FC) must be same!")
        # self.swift_id.swift_amt = self.remaining_swift_amount
        self.swift_id.encashment_rate_bdt = self.encashment_rate
        self.swift_id.encashment_rate_amnt = self.encashment_amount
        self.swift_id.encashment_bank_id = self.encashment_bank_id.id if self.encashment_bank_id else None
        self.swift_id.encashment_date = self.encashment_date
        self.swift_id.inter_bank_rate_bdt = self.inter_bank_rate_bdt
        self.swift_id.erq_bank_id = self.erq_bank_id.id

        #self.swift_id.bank_charge = self.bank_charge
        #self.swift_id.encashment_charge = self.encashment_charge
        #self.swift_id.swift_rate_bdt = self.swift_rate_bdt
        #self.swift_id.encashment_charge_bdt = self.encashment_charge_bdt
        #self.swift_id.other_charge = self.other_charge
        self.swift_id.remaining_swift_amount = self.remaining_swift_amount
        self.swift_id.is_erq_applicable = self.is_erq_applicable
        self.swift_id.erq_percentage = self.erq_percentage
        self.swift_id.bdt_encashment_percentage = self.bdt_encashment_percentage
        self.swift_id.erq_amount_bdt = self.erq_amount_bdt
        self.swift_id.bdt_encashment_amount = self.bdt_encashment_amount
        self.swift_id.fc_encashment_amount = self.fc_encashment_amount
        self.swift_id.erq_amount_fc = self.erq_amount_fc
        self.swift_id.remaining_swift_amount_bdt = self.remaining_swift_amount_bdt
        self.swift_id.difference_amnt_bdt = self.difference_amnt_bdt

        for rec in self.invoice_ids:
            if self.is_erq_applicable:
                rec.invoice_id.erq_amt_fc = rec.erq_fc
                rec.invoice_id.encashment_amt_fc = rec.encash_fc
            else:
                rec.invoice_id.encashment_amt_fc = rec.invoice_id.swift_amt

        self.swift_id.action_approve()

    def confirm_next(self):
        multiple = self.env.context.get('multiple')
        if multiple == '1':
            # ------------ invoice update
            if self.is_erq_applicable:
                if self.erq_amount_fc != self.erq_amount_fc_invoices:
                    raise exceptions.ValidationError("ERQ Amount (FC) and Invoices ERQ Amount (FC) must be same!")
            for rec in self.invoice_ids:
                if self.is_erq_applicable:
                    rec.invoice_id.erq_amt_fc = rec.erq_fc
                    rec.invoice_id.encashment_amt_fc = rec.encash_fc
                else:
                    rec.invoice_id.encashment_amt_fc = rec.invoice_id.swift_amt
            # ---------------

            active_ids = self.env.context.get('active_ids')
            for data in active_ids:
                swift_obj = self.env['swift.message'].sudo().browse(data)

                swift_obj.encashment_rate_bdt = self.encashment_rate
                swift_obj.encashment_rate_amnt = self.encashment_amount
                swift_obj.encashment_bank_id = self.encashment_bank_id.id if self.encashment_bank_id else None
                swift_obj.encashment_date = self.encashment_date
                swift_obj.inter_bank_rate_bdt = self.inter_bank_rate_bdt
                swift_obj.erq_bank_id = self.erq_bank_id.id

                #swift_obj.bank_charge = self.bank_charge
                #swift_obj.encashment_charge = self.encashment_charge
                #swift_obj.swift_rate_bdt = self.swift_rate_bdt
                #swift_obj.encashment_charge_bdt = self.encashment_charge_bdt
                #swift_obj.other_charge = self.other_charge
                swift_obj.remaining_swift_amount = self.remaining_swift_amount
                swift_obj.is_erq_applicable = self.is_erq_applicable
                swift_obj.erq_percentage = self.erq_percentage
                swift_obj.bdt_encashment_percentage = self.bdt_encashment_percentage
                swift_obj.erq_amount_bdt = self.erq_amount_bdt
                swift_obj.bdt_encashment_amount = self.bdt_encashment_amount
                swift_obj.fc_encashment_amount = self.fc_encashment_amount
                swift_obj.erq_amount_fc = self.erq_amount_fc
                swift_obj.remaining_swift_amount_bdt = self.remaining_swift_amount_bdt
                swift_obj.difference_amnt_bdt = self.difference_amnt_bdt

                # swift_obj.action_approve()
            action_ctx = dict(self.env.context)
            return {
                'name': _('Create Journal'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'journal.wizard',
                'view_id': False,
                'target': 'new',
                'context': {
                    'context': action_ctx,
                    'swift_id': active_ids,
                    'multiple': '1',
                    #'bank_charge': self.bank_charge,
                    'encashment_charge': self.encashment_charge,
                    #'swift_rate_bdt': self.swift_rate_bdt,
                    'encashment_charge_bdt': self.encashment_charge_bdt,
                    #'other_charge': self.other_charge,
                    'remaining_swift_amount': self.remaining_swift_amount,
                    'is_erq_applicable': self.is_erq_applicable,
                    'erq_percentage': self.erq_percentage,
                    'bdt_encashment_percentage': self.bdt_encashment_percentage,
                    'erq_amount_bdt': self.erq_amount_bdt,
                    'bdt_encashment_amount': self.bdt_encashment_amount,
                    'fc_encashment_amount': self.fc_encashment_amount,
                    'remaining_swift_amount_bdt': self.remaining_swift_amount_bdt,
                    'encashment_rate_bdt': self.encashment_rate,
                    'encashment_rate_amnt': self.encashment_amount,
                    'bank_id': self.bank_id.id,
                    'encashment_bank_id': self.encashment_bank_id.id if self.encashment_bank_id else None,
                    'encashment_date': self.encashment_date,
                    'inter_bank_rate_bdt': self.inter_bank_rate_bdt,
                    'difference_amnt_bdt': self.difference_amnt_bdt
                }
            }
        else:
            #------------ invoice update
            if self.is_erq_applicable:
                if self.erq_amount_fc != self.erq_amount_fc_invoices:
                    raise exceptions.ValidationError("ERQ Amount (FC) and Invoices ERQ Amount (FC) must be same!")
            for rec in self.invoice_ids:
                if self.is_erq_applicable:
                    rec.invoice_id.erq_amt_fc = rec.erq_fc
                    rec.invoice_id.encashment_amt_fc = rec.encash_fc
                else:
                    rec.invoice_id.encashment_amt_fc = rec.invoice_id.swift_amt
            #---------------

            self.swift_id.encashment_rate_bdt = self.encashment_rate
            self.swift_id.encashment_rate_amnt = self.encashment_amount
            self.swift_id.inter_bank_rate_bdt = self.inter_bank_rate_bdt

            #self.swift_id.bank_charge = self.bank_charge
            #self.swift_id.encashment_charge = self.encashment_charge
            # self.swift_id.swift_rate_bdt = self.swift_rate_bdt
            #self.swift_id.encashment_charge_bdt = self.encashment_charge_bdt
            #self.swift_id.other_charge = self.other_charge

            self.swift_id.remaining_swift_amount = self.remaining_swift_amount
            self.swift_id.is_erq_applicable = self.is_erq_applicable
            self.swift_id.erq_percentage = self.erq_percentage
            self.swift_id.bdt_encashment_percentage = self.bdt_encashment_percentage
            self.swift_id.erq_amount_bdt = self.erq_amount_bdt
            self.swift_id.bdt_encashment_amount = self.bdt_encashment_amount
            self.swift_id.fc_encashment_amount = self.fc_encashment_amount
            self.swift_id.erq_amount_fc = self.erq_amount_fc
            self.swift_id.remaining_swift_amount_bdt = self.remaining_swift_amount_bdt
            self.swift_id.encashment_bank_id = self.encashment_bank_id.id if self.encashment_bank_id else None,
            self.swift_id.erq_bank_id = self.erq_bank_id.id if self.erq_bank_id else None,
            self.swift_id.encashment_date = self.encashment_date
            self.swift_id.difference_amnt_bdt = self.difference_amnt_bdt

            self.swift_id.action_approve()
            action_ctx = dict(self.env.context)
            return {
                'name': _('Create Journal'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'journal.wizard',
                'view_id': False,
                'target': 'new',
                'context': {
                    'context': action_ctx,
                    'swift_id': self.swift_id.id,
                }
            }

class EncashmentRateWizardLine(models.TransientModel):
    """ To create probation period length """
    _name = 'en.rate.wizard.invoice'

    head_id = fields.Many2one('en.rate.wizard', string='Invoices', required=True, ondelete="cascade")
    is_erq_applicable = fields.Boolean(string='Is ERQ Applicable?', related="head_id.is_erq_applicable")

    invoice_id = fields.Many2one('cash.incentive.invoice', string='Invoices', ondelete="cascade")

    swift_fc = fields.Float(string='Encashable Swift (FC)', size=5, default=0)
    erq_fc = fields.Float(string='ERQ (FC)', size=5, default=0)
    encash_fc = fields.Float(string='Encashment (FC)', size=5, default=0, compute='_compute_encash_fc')

    @api.depends("swift_fc", "erq_fc", "is_erq_applicable")
    def _compute_encash_fc(self):
        for rec in self:
            if rec.is_erq_applicable:
                rec.encash_fc = (rec.swift_fc - rec.erq_fc)
            else:
                rec.encash_fc = rec.swift_fc
                rec.erq_fc = 0

    @api.constrains('erq_fc')
    def _check_erq_fc(self):
        for rec in self:
            if rec.erq_fc > rec.swift_fc:
                raise exceptions.ValidationError("ERQ (FC) can not be greater than Swift (FC) of Invoice:'" + rec.invoice_id.invoice_id.ref + "'!")