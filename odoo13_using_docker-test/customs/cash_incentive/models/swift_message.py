from odoo import models, fields, api, _, exceptions
import datetime
from odoo.exceptions import UserError
from odoo.addons.helper import validator
import base64, io, csv
from odoo.http import request


class SwiftMessage(models.Model):
    _name = "swift.message"
    _description = "SWIFT Message"
    _rec_name = "code"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    code = fields.Char(string='ERP Code', copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'), tracking=1)
    partner_id = fields.Many2one('res.partner', string='Customer', domain="[('type', '=', 'contact'), ('active', '=', True), ('customer_rank', '>', 0)]", tracking=13)
    remiter_bank_name = fields.Char("Remiter Bank Name", tracking=24)
    remiter_bank_address = fields.Text("Remiter Bank Address", tracking=25)
    swift_customer_name = fields.Char(string='SWIFT Customer Name', tracking=13)
    date = fields.Date(string='SWIFT Date', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('er', 'Encashment Rate'),
        ('pay', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, default='draft')
    swift_file = fields.Binary(string='SWIFT File (File- Received from Bank)', attachment=True, tracking=True)
    swift_file_name = fields.Char("File Name")
    ict_file = fields.Binary(string='ICT Form (Signed ICT Form, Received after Encashment)', attachment=True, tracking=True)
    ict_file_name = fields.Char("ICT Name")
    rate_file = fields.Binary(string='Rate Sheet', attachment=True, tracking=True)
    rate_file_name = fields.Char("Rate Sheet")
    bank_id = fields.Many2one('res.bank', string='Bank', domain="[('is_cash_incentive_bank', '=', True)]", tracking=17)
    erq_bank_id = fields.Many2one('res.bank', string='ERQ Bank', domain="[('is_cash_incentive_bank', '=', True)]",  tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", tracking=True)
    inv_names = fields.Char(string="Invoices", compute="_compute_inv_amt_count", store=True, tracking=True)
    incentive_file_no = fields.Char(string="Incentive File No.", compute="_compute_inv_amt_count", store=True, tracking=True) #search='_value_search_incentive'
    preparation_date = fields.Date(string='Preparation Date', compute="_compute_inv_amt_count", tracking=True)
    
    invoice_amt = fields.Float(string='Invoice Amount (FC)', store=True, compute="_compute_inv_amt_fc", digits=(16, 2), tracking=True)
    invoice_amt_bdt = fields.Float(string='Invoice Amount (BDT)', digits=(16, 2), store=True, compute="_compute_inv_amt_fc", tracking=True)

    swift_amt = fields.Float(string='Encashable SWIFT Amount (FC)', store=True, compute="_compute_inv_amt_fc", digits=(16, 2), tracking=True)
    swift_amt_bdt = fields.Float(string='Encashable Amount (BDT)', store=True, compute="_compute_inv_amt_fc", digits=(16, 2), tracking=True)
    encashment_charge = fields.Float(string='Bank Charge (FC)', digits=(16, 2), tracking=True)
    encashment_charge_bdt = fields.Float(string='Bank Charge (BDT)', digits=(16, 2), tracking=True)
    total_swift_amt = fields.Float(string='Receivable Credit (FC)', digits=(16, 2), tracking=True)
    total_swift_amt_bdt = fields.Float(string='Receivable Credit (BDT)', digits=(16, 2), tracking=True)

    is_code_change = fields.Boolean(default=False, copy=False, tracking=True)
    incentive_rate_fc = fields.Float(string='Incentive Rate (FC)(%)', digits=(16, 4), store=True, default=10, tracking=True)
    od_sight_rate = fields.Float(string='OD Sight Rate', digits=(16, 4), tracking=True)
    encashment_rate_bdt = fields.Float(string='Encashment Rate (BDT)', digits=(16, 2), store=True, tracking=True)
    inter_bank_rate_bdt = fields.Float(string='Inter-Bank Rate (BDT)', digits=(16, 4), tracking=True)
    encashment_rate_amnt = fields.Float(string='Encashment Amount (BDT)', digits=(16, 2), compute="_compute_inv_amt_fc", store=True, tracking=True)

    difference_amnt_bdt = fields.Float(string='Foreign Exchange Gain/Loss (BDT)', digits=(16, 2), default=0, tracking=True)
    encashment_bank_id = fields.Many2one('res.bank', string='Encashment Bank',
                                         domain="[('is_cash_incentive_bank', '=', True)]", tracking=17)
    encashment_date = fields.Date(string='Encashment Date', tracking=True)
    is_journal_created = fields.Boolean(default=False, tracking=True)
    encashment_forwarding_letter = fields.Html(string="Forwarding Letter")

    #swift_rate_bdt = fields.Float(string='SWIFT Rate (BDT)', digits=(16, 2))

    bank_charge = fields.Float(string='Bank Charge (FC)', digits=(16, 2), tracking=True)
    bank_charge_bdt = fields.Float(string='Bank Charge (BDT)', digits=(16, 2), tracking=True)
    other_charge = fields.Float(string='Other Charge (FC)', digits=(16, 2), tracking=True)
    other_charge_bdt = fields.Float(string='Other Charge (BDT)', digits=(16, 2), tracking=True)

    remaining_swift_amount = fields.Integer(string='Remaining Swift Amount (FC)', tracking=6)
    remaining_swift_amount_bdt = fields.Float(string='Remaining Swift Amount (BDT)', digits=(16, 2), tracking=True)

    erq_amount_fc = fields.Float(string='ERQ Amount (FC)', digits=(16, 2), tracking=True)
    fc_encashment_amount = fields.Float(string='Encashment Amount (FC) ', digits=(16, 2), tracking=True)
    is_erq_applicable = fields.Boolean(string='Is ERQ Applicable?', default=False, tracking=True)
    erq_percentage = fields.Float(string='ERQ Percentage', digits=(16, 4), tracking=True)
    bdt_encashment_percentage = fields.Float(string='BDT Encashment Percentage', digits=(16, 4), tracking=True)
    erq_amount_bdt = fields.Float(string='ERQ Amount (BDT)', digits=(16, 2), tracking=True)
    bdt_encashment_amount = fields.Float(string='Encashment Amount (BDT) ', digits=(16, 2), tracking=True)
    move_id = fields.Many2one('account.move')
    incentive_deadline = fields.Date(string='Cash Incentive Deadline', tracking=5,
                                       help='Incentive Deadline Will be 179 Days More than SWIFT Date',
                                       compute='_compute_inv_amt_fc')
    remaining_days = fields.Integer(string='Remaining days', compute='_compute_remaining_day', tracking=6, search='_value_search')
    form_c_description = fields.Html(string="Letter Template")

    # comment-for-upgrade
    #---------------
    # partner_cr_acc_id = fields.Many2one('account.account', 'Credit Account', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # encashment_acc_id = fields.Many2one('account.account', 'Encashment (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # bank_charge_acc_id = fields.Many2one('account.account', 'Bank Charge (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # fc_gain_loss_acc_id = fields.Many2one('account.account', 'Foreign Exchange Gain/Loss', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # erq_acc_id = fields.Many2one('account.account', 'ERQ (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    #-----------------

    partner_cr_acc_id = fields.Many2one('account.account', 'Credit Account', tracking=True)
    encashment_acc_id = fields.Many2one('account.account', 'Encashment (Dr.)', tracking=True)
    bank_charge_acc_id = fields.Many2one('account.account', 'Bank Charge (Dr.)', tracking=True)
    fc_gain_loss_acc_id = fields.Many2one('account.account', 'Foreign Exchange Gain/Loss', tracking=True)
    erq_acc_id = fields.Many2one('account.account', 'ERQ (Dr.)', tracking=True)

    date_credited_beneficiaries = fields.Date(string='Date Credited Beneficiaries', tracking=10)
    reporting_st_to_bb = fields.Char(string='Reporting statement/schedule to BB with Month', tracking=11)
    ref_online_to_bb = fields.Char(string='Reference of Online reporting to BB', tracking=12)

    def _value_search(self, operator, value):
        recs = self.search([]).filtered(lambda x: x.remaining_days <= value)
        if recs:
            return [('id', 'in', [x.id for x in recs] if recs else False)]
        else:
            return [('id', '!=', 0)]

    # def _value_search_inoices(self, operator, value):
    #     #rows = self.search([]).filtered(lambda x: x.inv_names 'ilike' value)
    #     rows = self.env['swift.message'].search([('inv_names','ilike',value)])
    #
    #     #self.env['swift.message'].search([('incentive_file_no', '!=', '')])
    #     if rows:
    #         return [('id', 'in', [x.id for x in rows] if rows else False)]
    #     else:
    #         return [('id', '!=', 0)]

    def _value_search_incentive(self, operator, value):
        recs = self.search([]).filtered(lambda x: x.incentive_file_no == value)
        # all_inv = self.env['swift.message'].search([('incentive_file_no', '!=', '')])
        # print(all_inv)
        if value == 'filled':
            recs = self.search([]).filtered(lambda x: x.incentive_file_no != '')
        else:
            recs = self.search([]).filtered(lambda x: x.incentive_file_no == '')
        if recs:
            return [('id', 'in', [x.id for x in recs] if recs else False)]
        else:
            return [('id', '!=', 0)]




    # @api.depends('date')
    # def _compute_incentive_deadline(self):
    #     for rec in self:
    #         if rec.date:
    #             rec.incentive_deadline = rec.date + datetime.timedelta(days=179)
    #         else:
    #             rec.incentive_deadline = None

    @api.depends("incentive_deadline")
    def _compute_remaining_day(self):
        for rec in self:
            today = fields.Date.today()
            incentive_deadline = rec.incentive_deadline
            remaining_days = 0
            if today and incentive_deadline:
                try:
                    remaining_days = (incentive_deadline - today).days
                except:
                    remaining_days = 0
            rec.remaining_days = remaining_days

    # def _compute_inv_count(self):
    #     for rec in self:
    #         all_inv = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', rec.id)])
    #         total_count = len(all_inv)
    #         rec.inv_count = total_count
    #
    #         self._compute_inv_amt_fc()

    # inv_count = fields.Integer(compute='_compute_inv_count', string='Invoice Count')
    inv_count = fields.Integer(compute="_compute_inv_amt_count", string='Invoice Count')
    inv_file_count = fields.Integer(compute="_compute_inv_amt_count", string='File Count')

    @api.onchange('od_sight_rate')
    def onchange_od_sight_rate(self):
        if self.od_sight_rate:
            all_inv = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', self._origin.id)])
            for rec in all_inv:
                rec.od_sight_rate = self.od_sight_rate

    # @api.onchange('date_credited_beneficiaries')
    # def onchange_date_credited_beneficiaries(self):
    #     if self.date_credited_beneficiaries:
    #         try:
    #             dt_str = str(self.date_credited_beneficiaries.strftime('%m %Y'))
    #         except:
    #             dt_str = ''
    #
    #         self.reporting_st_to_bb = 'J-1, O-3/'+ dt_str

    @api.onchange('date_credited_beneficiaries', 'reporting_st_to_bb', 'ref_online_to_bb')
    def onchange_date_credited_beneficiaries(self):
        if self.date_credited_beneficiaries or self.reporting_st_to_bb or self.ref_online_to_bb:
            if self.date_credited_beneficiaries:
                try:
                    dt_str = str(self.date_credited_beneficiaries.strftime('%B %Y'))
                except:
                    dt_str = ''

                self.reporting_st_to_bb = 'J-1, O-3/' + dt_str
            #-----------------

            all_inv = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', self._origin.id)])
            for rec in all_inv:
                rec.date_credited_beneficiaries = self.date_credited_beneficiaries
                rec.reporting_st_to_bb = self.reporting_st_to_bb
                rec.ref_online_to_bb = self.ref_online_to_bb

    @api.onchange('currency_id','date','bank_id')
    def onchange_currency_id_date_bank(self):
        if self.currency_id and self.date and self.bank_id:
            for rec in self:
                currency_rate_obj = self.env['currency.conversion.rate'].search(
                    [('date', '<=', rec.date), ('bank_id', '=', rec.bank_id.id), ('currency_id', '=', rec.currency_id.id),
                     ('type', '=', '04')], order='date DESC', limit=1)
                if currency_rate_obj:
                    rec.od_sight_rate = currency_rate_obj.rate
                else:
                    rec.od_sight_rate = 0

    @api.depends("partner_id", "inv_count")
    def _compute_inv_amt_count(self):
        for rec in self:
            inv_ids = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', rec.id)])
            total_count = len(inv_ids)
            rec.inv_count = total_count
            
            inv_names = ''
            incentive_file_no = ''
            incentive_file = []
            preparation_date = None
            for x in inv_ids:
                if x.invoice_id.ref:
                    inv_names += x.invoice_id.ref if not inv_names else ', ' + x.invoice_id.ref
                if x.head_id.name:
                    if x.head_id.id not in incentive_file:
                        incentive_file_no += x.head_id.name if not incentive_file_no else ', ' + x.head_id.name
                        incentive_file.append(x.head_id.id)

                if x.head_id.date:
                    preparation_date = x.head_id.date
            rec.inv_names = inv_names
            rec.incentive_file_no = incentive_file_no
            rec.preparation_date = preparation_date
            rec.inv_file_count = len(incentive_file)

    @api.depends("date")
    def _compute_inv_amt_fc(self):
        for rec in self:
            if rec.date:
                rec.incentive_deadline = rec.date + datetime.timedelta(days=179)
            else:
                rec.incentive_deadline = None
                
            inv_ids = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', rec.id)])
            invoice_amt = 0
            invoice_amt_bdt = 0
            swift_amt = 0
            swift_amt_bdt = 0
            swift_charge_fc = 0
            swift_charge_bdt = 0
            encashment_rate_amnt = 0
            if inv_ids:
                invoice_amt = sum(inv_ids.mapped('invoice_amt'))
                invoice_amt_bdt = sum(inv_ids.mapped('invoice_amt_bdt'))
                swift_amt = sum(inv_ids.mapped('swift_amt'))
                swift_amt_bdt = sum(inv_ids.mapped('swift_amt_bdt'))
                swift_charge_fc = sum(inv_ids.mapped('swift_charge_fc'))
                swift_charge_bdt = sum(inv_ids.mapped('swift_charge_bdt'))
                encashment_rate_amnt = sum(inv_ids.mapped('encashment_amt_bdt'))

            rec.invoice_amt = invoice_amt
            rec.invoice_amt_bdt = invoice_amt_bdt
            rec.swift_amt = swift_amt
            rec.swift_amt_bdt = swift_amt_bdt

            rec.encashment_charge = swift_charge_fc
            rec.encashment_charge_bdt = swift_charge_bdt

            rec.total_swift_amt = swift_amt + swift_charge_fc
            rec.total_swift_amt_bdt = swift_amt_bdt + swift_charge_bdt

            rec.encashment_rate_amnt = encashment_rate_amnt

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.swift_customer_name = self.partner_id.name.upper()
        
    @api.onchange('swift_customer_name','remiter_bank_name','remiter_bank_address')
    def onchange_uppercase_name(self):
        if self.swift_customer_name:
            self.swift_customer_name = self.swift_customer_name.upper()
        if self.remiter_bank_name:
            self.remiter_bank_name = self.remiter_bank_name.upper()
        if self.remiter_bank_address:
            self.remiter_bank_address = self.remiter_bank_address.upper()

    def action_account_move_journal(self):
        account_move_obj = self.env['account.move'].search([('swift_id', '=', self.id)])
        if not self.move_id.id:
            raise UserError(_('No Journal Entry Found.'))
        action_vals = {
            'name': _('Journal'),
            'domain': [('id', '=', self.move_id.id)],
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_type': 'entry',
            }
        }
        return action_vals

    # @api.depends('invoice_amt_bdt','encashment_rate_amnt','encashment_rate_bdt')
    # def _compute_difference_amnt_bdt(self):
    #     for rec in self:
    #         #'bank_charge','other_charge',
    #         #previous_amnt = rec.invoice_amt_bdt - rec.encashment_rate_amnt - (rec.bank_charge*rec.encashment_rate_bdt + rec.other_charge*rec.encashment_rate_bdt)
    #         previous_amnt = rec.encashment_rate_amnt - rec.invoice_amt_bdt
    #         rec.difference_amnt_bdt = previous_amnt

        # if self.is_erq_applicable:
        #     self.difference_amnt_bdt = (self.erq_amount_bdt + self.bdt_encashment_amount) - self.swift_amt_bdt
        # else:
        #     self.difference_amnt_bdt = self.encashment_amount - self.swift_amt_bdt

    def action_receivable_journal(self):
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
                'swift_id': self.id,
            }
        }
    
    def action_incentive_invoice(self):
        inv_ids = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', self.id)]).ids
        domain = []
        domain.append(('id', 'in', inv_ids))
        action_vals = {
            'name': _('SWIFT Invoice'),
            'domain': domain,
            'res_model': 'cash.incentive.invoice',
            'view_mode':  'tree,form',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        if self.state in ['er', 'pay', 'cancel']:
            action_vals['context'] = {'default_swift_message_id': self.id, 'default_partner_id': self.partner_id.id, 'is_show': False, 'create': False, 'delete': False}
        else:
            action_vals['context'] = {'default_swift_message_id': self.id, 'default_partner_id': self.partner_id.id, 'is_show': False, 'create': True, 'delete': True}
        # if len(product_qc_ids) < 1:
        #     action_vals.update({'res_id': False, 'view_mode': 'form'})
        # else:

        return action_vals

    def action_invoice_files(self):
        inv_ids = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', self.id)]).head_id
        file_ids=[]
        for rec in inv_ids:
            file_ids.append(rec.id)

        file_ids=list(set(file_ids))
        if len(file_ids) == 0:
            raise UserError(_('File not available!.'))
        else:
            domain = []
            domain.append(('id', 'in', file_ids))
            action_vals = {
                'name': _('Cash Incentive'),
                'domain': domain,
                'res_model': 'cash.incentive.head',
                'view_mode':  'tree,form',
                'view_id': False,
                'type': 'ir.actions.act_window',
            }

            if self.state in ['er', 'pay', 'cancel']:
                action_vals['context'] = {'default_swift_message_id': self.id, 'default_partner_id': self.partner_id.id,
                                          'is_show': False, 'create': False, 'delete': False}
            else:
                action_vals['context'] = {'default_swift_message_id': self.id, 'default_partner_id': self.partner_id.id,
                                          'is_show': False, 'create': True, 'delete': True}

            return action_vals

    def action_en_rate(self):
        inv_ids = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', self.id)]).ids
        if len(inv_ids) < 1:
            raise UserError(_('No Invoices!.'))
        if self.swift_amt < 1:
            raise UserError(_('Swift Amount can not be 0!.'))
        action_ctx = dict(self.env.context)
        return {
            'name': _('Encashment Rate'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'en.rate.wizard',
            'view_id': False,
            'target': 'new',
            'context': {
                'context': action_ctx,
                'swift_id': self.id,
            }
        }

    # @api.constrains('code')
    # def _check_unique_code(self):
    #     envobj = self.env['client.contract']
    #     for rec in self:
    #         msg = '"%s"' % rec.code
    #         record = envobj.sudo().search([('id', '!=', rec.id), ('code', '=', rec.code)], limit=1)
    #         if record:
    #             raise exceptions.ValidationError("'" + msg + "' already exists!")

    def action_add_invoice(self):
        pass

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        for rec in self:
            if not rec.is_code_change:
                rec.code = self.env['ir.sequence'].get('swift_code')
            rec.state = 'confirm'
            rec.is_code_change = True

    def action_approve(self):
        all_swift = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', self.id)])
        for rec in all_swift:
            if rec.invoice_id.swift_remaining_amount > 0:
                rec.invoice_id.swift_remaining_amount -= rec.total_swift_amt
                if rec.invoice_id.swift_remaining_amount == 0:
                    rec.invoice_id.is_done_inv_amount = True
            else:
                rec.invoice_id.swift_remaining_amount = rec.invoice_amt - rec.total_swift_amt
                if rec.invoice_id.swift_remaining_amount == 0:
                    rec.invoice_id.is_done_inv_amount = True
        self.state = 'er'

    def action_cancel(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only Draft record can be cancelled!.'))
            else:
                self.state = 'cancel'

    # forwarding ------------------
    def action_get_template_fl(self):
        prc_text = self.bank_id.encashment_forwarding_letter
        today = fields.Date.today()
        currency = ''
        if self.currency_id:
            currency = self.currency_id.name
        final_text = ''
        if prc_text:
            final_text = prc_text.replace('$date', str(today)).replace('$bank_name', str(self.bank_id.name))\
                .replace('$encashment_amount',str(currency) + str(self.encashment_rate_amnt))\
                .replace('$customer_name', str(self.partner_id.name))
        self.encashment_forwarding_letter = final_text

    # c -------------------
    def action_refresh_form_c(self):
        currency = ''
        if self.currency_id:
            currency = self.currency_id.name
        client_name = ''
        customer_address = ''
        if self.partner_id:
            client_name = self.partner_id.name

        customer_address = self.partner_id.street2

        inv_number = ''
        encashment_amt_bdt_total = 0
        inv_amount = 0
        # #inv_date = ''
        swift_id = None
        invoice_line_ids = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', self.id)])
        contract_price_str = ''
        contract_id = []
        for rec in invoice_line_ids:
            inv_number += str(rec.invoice_id.ref) if not inv_number else ', ' + str(rec.invoice_id.ref)
            inv_amount += rec.invoice_amt
            encashment_amt_bdt_total += rec.encashment_amt_bdt
            swift_id = rec.swift_message_id
            for l in rec.invoice_id.contract_ids:
                if l.id not in contract_id:
                    if l.type == '0' and l.range:
                        contract_price_str += str(l.range) if not contract_price_str else ', ' + str(l.range)

            # inv_date += str(rec.invoice_date) if not inv_date else ', ' + str(rec.invoice_date)
        remiter_address = ''
        if swift_id:
            if swift_id.remiter_bank_name:
                remiter_address += swift_id.remiter_bank_name
            if swift_id.remiter_bank_address:
                remiter_address += swift_id.remiter_bank_address if not remiter_address else ', ' + swift_id.remiter_bank_address
        description_text = self.bank_id.form_c_description
        final_text = ''
        if description_text:
            final_text = description_text.replace('$currency', str(currency)).replace('$total_amount',
                                                                                      str(contract_price_str)).replace(
                '$client_name', str(client_name)).replace('$client_address', str(customer_address)).replace(
                '$invoice_number', str(inv_number)).replace('$bdt_amount', str(inv_amount)).replace('$date',
                                                                                                    str(self.date)).replace(
                '$remiter_address', str(remiter_address))
        self.form_c_description = final_text

    def action_print_with_head(self):
        type = self.env.context.get('type')
        with_head = self.env.context.get('with_head')
        data = {}
        result = []
        rpt_name = ''
        # if type == 'fl':
        #     result.append({'details': self.encashment_forwarding_letter})
        #     rpt_name = 'PRC Report'
        # if type == 'FORM_C':
        #     result.append({'details': self.form_c_description})
        #     rpt_name = 'ICT Report'
        data['ids'] = result
        data['with_head'] = with_head
        data['rpt_name'] = type
        data['swift_id'] = self.id

        return self.env.ref('cash_incentive.report_incentive_letter_w_head').with_context(landscape=False).report_action(self, data=data)


class SwiftMessageInvoice(models.Model):
    _name = "swift.message.invoice"
    _description = "Swift Message Invoice"
    _rec_name = "invoice_id"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    code = fields.Char(string='ERP Code', copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'), tracking=1)
    partner_id = fields.Many2one('res.partner', string='Customer',  tracking=13)
    invoice_id = fields.Many2one('account.move', string='Invoices', required=True, ondelete='cascade')
    remiter_bank_name = fields.Char("Remiter Bank Name", tracking=24)
    remiter_bank_address = fields.Text("Remiter Bank Address", tracking=25)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, default='draft')
    swift_file = fields.Binary(string='Swift File', attachment=True)
    swift_file_name = fields.Char("File Name")