from datetime import datetime
from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError
import calendar
from num2words import num2words


class AccountMoveInheritCashIncentive(models.Model):
    _inherit = 'account.move'
    _rec_name = 'ref'

    contract_ids = fields.Many2many("client.contract", string="Contract/PO/Ref", copy=False)
    foreign_currency_type = fields.Many2one('res.currency', 'Foreign Currency', domain="[('name', '!=', 'BDT')]", copy=False)
    usd_rate = fields.Float(string='BDT Rate', digits=(16, 4), copy=False)
    currency_symbol = fields.Char(string="Currency Symbol", copy=False)
    reference_number = fields.Char(string="Reference Number", copy=True)
    day_book_sl = fields.Integer(string="Reference Number", copy=False)
    day_book_month_sl = fields.Char(string="Reference Number", copy=False)
    customer_country_id = fields.Many2one('res.country', related='partner_id.country_id')

    cash_incentive_id = fields.Many2one('cash.incentive.head')
    cash_incentive_date = fields.Date(related='cash_incentive_id.date')

    swift_id = fields.Many2one('swift.message', string='SWIFT')
    swift_date = fields.Date(related='swift_id.date')
    swift_bank_id = fields.Many2one(related='swift_id.bank_id')
    swift_od_sight_rate = fields.Float(related='swift_id.od_sight_rate')
    encashment_bank_id = fields.Many2one(related='swift_id.encashment_bank_id')
    encashment_date = fields.Date(related='swift_id.encashment_date')
    encashment_rate_bdt = fields.Float(related='swift_id.encashment_rate_bdt')
    encashment_remaining_days = fields.Integer(related='swift_id.remaining_days')

    partner_address = fields.Text(string="Address", copy=False)
    mashuk_challan_no = fields.Char(string="Mushak Challan No.", copy=False)
    mashuk_challan_date = fields.Date(string="Mushak Challan Date", copy=False)
    swift_remaining_amount = fields.Float(copy=False)

    invoice_total_actual_amt = fields.Float(copy=False, string='Invoice Total (FC)', compute='_compute_invoice_total_fc', store=True)
    invoice_disc_fc_amt = fields.Float(copy=False, string='Invoice Discount (FC)', default=0)

    invoice_total_fc = fields.Float(copy=False, string='Invoice Net Total (FC)', compute='_compute_invoice_total_fc', store=True)
    invoice_payment_amount_fc = fields.Float(copy=False, string='Paid Amount (FC)')
    invoice_remaining_amount_fc = fields.Float(copy=False, compute='_compute_invoice_payment_amount_fc', string='Due Amount (FC)', store=True)
    is_done_inv_amount = fields.Boolean(default=False, copy=False)
    invoice_customer_type = fields.Selection(related='partner_id.vendor_type', string='Type (Local/Foreign)')
    partner_code = fields.Char(string='Partner Code', default='')
    vendor_code = fields.Char(string='Code', readonly=True, default='')
    total_discount_amount = fields.Monetary(string='Total Discount', compute='_compute_total_discount_amount', currency_field='company_currency_id', store=True)
    total_price_amount = fields.Monetary(string='Total Amount', compute='_compute_total_price_amount',
                                         currency_field='company_currency_id')
    payment_amount = fields.Monetary(string='Payment Amount', compute='_compute_payment_amount',
                                     currency_field='company_currency_id')
    location_id = fields.Many2one('stock.location', string='Location')

    dis_type = fields.Selection([
        ('foreign', 'Foreign'),
        ('local', 'Local')
    ], string='Discount Type', copy=False, default='foreign')
    fixed_discount = fields.Float(string="Fixed Disc.", digits="Product Price", default=0.000)
    percentage_discount = fields.Float(string='% Disc.', digits=(16, 4), default=0.0)
    def _compute_amount_in_word(self):
        for rec in self:
            rec.amount_in_words = "".join(num2words(rec.amount_total, lang='en_IN').title().replace("-", " ")).replace(
                ",", "") + " Taka Only"

    amount_in_words = fields.Char(string="Amount In Words:", compute='_compute_amount_in_word')

    @api.model
    def __def_terms_condition(self):
        terms_cond = self.env['invoice.terms.condition'].search([('id', '!=', False)], order="id asc", limit=1)
        return terms_cond.id

    terms_condition_id = fields.Many2one('invoice.terms.condition', string='Terms & Condition Title',
                                        default=lambda self: self.__def_terms_condition())
    terms_condtion_details = fields.Html('Terms Condition Details')

    @api.model
    def create(self, vals):
        res = super(AccountMoveInheritCashIncentive, self).create(vals)
        if res.move_type == 'entry':
            a = "'" + str(res.date.month) + "'"
            self.env.cr.execute(
                """select day_book_sl from account_move  where move_type = 'entry' and day_book_month_sl = %s order by id desc limit 1""" % a)
            totalraw = self.env.cr.fetchone()
            if totalraw:
                if totalraw[0] != None:
                    last_sl = totalraw[0] + 1
                else:
                    last_sl = 1
            else:
                last_sl = 1
            last_sl_no = str(last_sl)
            res.reference_number = str(calendar.month_abbr[res.date.month]) + "-" + str(last_sl_no).zfill(4)
            res.day_book_sl = last_sl
            res.day_book_month_sl = res.date.month
        # month = str(emp_joining_dtime.month).zfill(2)
        return res

    def write(self, vals):
        if 'total_discount_amount' in vals:
            if vals['total_discount_amount']:
                vals['amount_total'] = vals['amount_untaxed']
        super(AccountMoveInheritCashIncentive, self).write(vals)
        for rec in self:
            if rec.move_type == 'entry':
                if 'date' in vals:
                    date_time_obj = datetime.strptime(str(vals['date']), '%Y-%m-%d')
                    a = "'" + str(rec.date.month) + "'"
                    self.env.cr.execute(
                        """select day_book_sl from account_move  where move_type = 'entry' and day_book_month_sl = %s order by id desc limit 1""" % a)
                    totalraw = self.env.cr.fetchone()
                    if totalraw:
                        if totalraw[0] != None:
                            if str(date_time_obj.month) != self.day_book_month_sl:
                                last_sl = totalraw[0] + 1
                            else:
                                last_sl = totalraw[0]
                        else:
                            last_sl = 1
                    else:
                        last_sl = 1
                    last_sl_no = str(last_sl)
                    rec.reference_number = str(calendar.month_abbr[rec.date.month]) + "-" + str(last_sl_no).zfill(4)
                    rec.day_book_sl = last_sl
                    rec.day_book_month_sl = rec.date.month

        # return super(AccountMoveInheritCashIncentive, self).write(vals)
    
    @api.constrains('percentage_discount', 'fixed_discount', 'usd_rate')
    def _check_fixed_discount(self):
        for rec in self:
            if rec.fixed_discount < 0 or rec.percentage_discount < 0 or rec.usd_rate < 0:
                raise UserError(_('Amount can not be negative!.'))
            
    @api.depends('invoice_line_ids.qty_usd_price', 'invoice_line_ids.usd_price', 'usd_rate')
    def _compute_invoice_total_fc(self):
        for rec in self:
            inv_ids = self.env['account.move.line'].search([('move_id', '=', rec.id)])
            if inv_ids:
                qty_usd_price = sum(inv_ids.mapped('qty_usd_price'))
            else:
                qty_usd_price = sum(self.invoice_line_ids.mapped('qty_usd_price'))
            rec.invoice_total_fc = qty_usd_price - rec.fixed_discount
            rec.invoice_total_actual_amt = qty_usd_price
            rec.total_price_amount = rec.amount_untaxed + rec.total_discount_amount

    @api.depends('invoice_payment_amount_fc', 'invoice_total_fc')
    def _compute_invoice_payment_amount_fc(self):
        for rec in self:
            rec.invoice_remaining_amount_fc = rec.invoice_total_fc - rec.invoice_payment_amount_fc

    @api.constrains('ref')
    def _check_unique_ref(self):
        for rec in self:
            envobj = self.env['account.move']
            msg = 'Reference "%s"' % rec.ref
            records=[]
            if rec.move_type == 'out_invoice':
                records = envobj.sudo().search([('id', '!=', rec.id), ('ref', '=', rec.ref)], limit=1)
            if records:
                raise exceptions.ValidationError("'" + msg + "' already exists!")

    @api.onchange('dis_type')
    def _onchange_dis_type(self):
        if not self.dis_type:
            self.fixed_discount = 0
            self.percentage_discount = 0
            self.invoice_total_fc = self.invoice_total_actual_amt

            self.total_discount_amount = 0
            self.amount_untaxed = self.total_price_amount - self.total_discount_amount
            self.amount_total = self.total_price_amount - self.total_discount_amount

        if self.dis_type == 'local':
            self.invoice_total_fc = self.invoice_total_actual_amt

        if self.dis_type == 'foreign':
            self._onchange_fixed_discount()

    @api.onchange('invoice_line_ids')
    def _onchange_discount_amount(self):
        # super(AccountMoveInheritCashIncentive, self)._onchange_discount_amount()
        for rec in self:
            if len(rec.invoice_line_ids) < 1:
                rec.total_discount_amount = 0
                rec.amount_untaxed = rec.total_price_amount - rec.total_discount_amount
                rec.amount_total = rec.total_price_amount - rec.total_discount_amount

            if rec.dis_type == 'foreign':
                rec.total_discount_amount = rec.fixed_discount * self.usd_rate
            else:
                rec.total_discount_amount = rec.fixed_discount

            rec.amount_untaxed = rec.total_price_amount - rec.total_discount_amount
            rec.amount_total = rec.total_price_amount - rec.total_discount_amount

    @api.onchange('percentage_discount', 'usd_rate')
    def _onchange_percentage_discount(self):
        for line in self:
            if len(line.invoice_line_ids) < 1:
                line.total_discount_amount = 0
                line.amount_untaxed = line.total_price_amount - line.total_discount_amount
                line.amount_total = line.total_price_amount - line.total_discount_amount

            if line.dis_type == 'foreign':
                if line.percentage_discount != 0 and line.percentage_discount > 0:
                    if self.percentage_discount > 99:
                        raise exceptions.ValidationError(_("Discount can't be 100%!"))
                    self.fixed_discount = 0.0
                    fixed_discount = (line.invoice_total_actual_amt) * (line.percentage_discount / 100.0)
                    line.update({"fixed_discount": fixed_discount})
                    self.invoice_total_fc = self.invoice_total_actual_amt - self.fixed_discount
                    self.total_discount_amount = fixed_discount * self.usd_rate
                    self.amount_untaxed = self.total_price_amount - self.total_discount_amount
                    self.amount_total = self.total_price_amount - self.total_discount_amount
                if line.percentage_discount == 0:
                    fixed_discount = 0.000
                    line.update({"fixed_discount": fixed_discount})
                    self.invoice_total_fc = self.invoice_total_actual_amt - self.fixed_discount
                    self.total_discount_amount = 0
                    self.amount_untaxed = self.total_price_amount - self.total_discount_amount
                    self.amount_total = self.total_price_amount - self.total_discount_amount
            else:
                self.invoice_total_fc = self.invoice_total_actual_amt
                if line.dis_type == 'local':
                    if line.percentage_discount != 0 and line.percentage_discount > 0:
                        fixed_discount = (line.total_price_amount) * (line.percentage_discount / 100.0)
                        self.fixed_discount = fixed_discount
                        self.total_discount_amount = fixed_discount
                        self.amount_untaxed = self.total_price_amount - self.total_discount_amount
                        self.amount_total = self.total_price_amount - self.total_discount_amount

    @api.onchange('fixed_discount', 'usd_rate')
    def _onchange_fixed_discount(self):
        for line in self:
            if len(line.invoice_line_ids) < 1:
                line.total_discount_amount = 0
                line.amount_untaxed = line.total_price_amount - line.total_discount_amount
                line.amount_total = line.total_price_amount - line.total_discount_amount

            if line.dis_type == 'foreign':
                if line.fixed_discount != 0 and line.fixed_discount > 0:
                    if line.fixed_discount > line.invoice_total_actual_amt:
                        line.fixed_discount = 0
                        raise exceptions.ValidationError(_("Discount can't be greater than FC Subtotal!"))
                    self.percentage_discount = 0.0
                    discount = ((self.invoice_total_actual_amt) - (self.invoice_total_actual_amt - self.fixed_discount)) / (self.invoice_total_actual_amt) * 100 or 0.0
                    if discount > 99:
                        raise exceptions.ValidationError(_("Discount can't be 100%!"))
                    line.update({"percentage_discount": discount})
                    self.invoice_total_fc = self.invoice_total_actual_amt - self.fixed_discount
                    self.total_discount_amount = self.fixed_discount * self.usd_rate
                    self.amount_untaxed = self.total_price_amount - self.total_discount_amount
                    self.amount_total = self.total_price_amount - self.total_discount_amount
                if line.fixed_discount == 0:
                    discount = 0.0
                    line.update({"percentage_discount": discount})
                    self.invoice_total_fc = self.invoice_total_actual_amt - self.fixed_discount
                    self.total_discount_amount = 0
                    self.amount_untaxed = self.total_price_amount - self.total_discount_amount
                    self.amount_total = self.total_price_amount - self.total_discount_amount
            else:
                self.invoice_total_fc = self.invoice_total_actual_amt
                if line.dis_type == 'local':
                    if line.fixed_discount != 0 and line.fixed_discount > 0:
                        discount = ((self.total_price_amount) - (self.total_price_amount - self.fixed_discount)) / (self.total_price_amount) * 100 or 0.0
                        if discount > 99:
                            raise exceptions.ValidationError(_("Discount can't be 100%!"))
                        self.percentage_discount = discount
                        self.total_discount_amount = self.fixed_discount
                        self.amount_untaxed = self.total_price_amount - self.total_discount_amount
                        self.amount_total = self.total_price_amount - self.total_discount_amount

    @api.onchange('terms_condition_id')
    def onchange_terms_condition_id(self):
        if self.terms_condition_id:
            self.terms_condtion_details = self.terms_condition_id.description
        else:
            self.terms_condtion_details = ''

    def _compute_swift_count(self):
        all_swift = self.env['cash.incentive.invoice'].search([('invoice_id', '=', self.id), ('swift_message_id', '!=', False)])
        self.swift_count = len(all_swift)

    def _compute_incentive_count(self):
        all_incentive = self.env['cash.incentive.invoice'].search([('invoice_id', '=', self.id), ('head_id', '!=', False)])
        self.incentive_count = len(all_incentive)

    swift_count = fields.Integer(compute='_compute_swift_count', string='SWIFT Count')
    incentive_count = fields.Integer(compute='_compute_incentive_count', string='Incentive Count')

    def _compute_payment_amount(self):
        # super(AccountMoveInheritCashIncentive, self)._compute_payment_amount()
        for rec in self:
            rec.payment_amount = 0

    def calculate_discount(self):
        dis_pro_id = self.env['product.product'].search([('is_default_discount_product', '=', True)], limit=1)
        if not dis_pro_id:
            raise UserError(_('No Default Discount Product Assigned!.'))

        move_lines = []
        pre_applied = False
        pre_line_id = False
        for data in self.line_ids:
            # if data.debit != 0 and data.name == 'Discount':
            if data.product_id.is_default_discount_product:
                pre_applied = True
                pre_line_id = data
                if data.debit == self.total_discount_amount:
                    return
                    # raise UserError(_('Nothing New to Calculate Discount.'))

        for data in self.line_ids:
            if data.debit != 0 and data.name != 'Discount':
                amount = self.amount_untaxed
                move_lines.append((1, data.id, {
                    'debit': amount,
                    'credit': 0.0,
                }))
                break

        if pre_applied:
            move_lines.append((1, pre_line_id.id, {
                'debit': self.total_discount_amount,
                'price_unit': (-1 * self.total_discount_amount),
                'credit': 0.0,
            }))
        else:
            move_lines.append(
                (0, 0, {
                    'product_id': dis_pro_id.id,
                    'price_unit': (-1 * self.total_discount_amount),
                    'quantity': 1,
                    'currency_id': False,
                    'partner_id': self.partner_id.id,
                    'name': 'Discount',
                    'account_id': dis_pro_id.product_tmpl_id.property_account_income_id.id,
                    'exclude_from_invoice_tab': True,
                }),
            )
        self.write({
            'payment_amount': 0,
            'line_ids': move_lines,
        })

    def action_post(self):
        if self.fixed_discount:
            self.calculate_discount()
        res = super(AccountMoveInheritCashIncentive, self).action_post()
        amount = 0
        if self.fixed_discount:
            for data in self.line_ids:
                if data.debit != 0 and data.name != 'Discount':
                    amount = data.debit
            if self.amount_total != amount:
                raise UserError(_('Please Calculate Discount.'))
        return res

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state')
    def _compute_amount(self):
        super(AccountMoveInheritCashIncentive, self)._compute_amount()
        for rec in self:
            if rec.total_discount_amount:
                rec.amount_untaxed = rec.amount_untaxed - rec.total_discount_amount
                rec.amount_total = rec.amount_untaxed

    def js_python_method(self, model_name, active_id):
        pass

    def action_get_incentive_count(self):
        all_incentive = self.env['cash.incentive.invoice'].search([('invoice_id', '=', self.id), ('head_id', '!=', False)])
        req_ids = []
        for rec in all_incentive:
            req_ids.append(rec.head_id.id)
        if not req_ids:
            raise UserError(_('No Incentive Found.'))
        action_vals = {
            'name': _('Cash Incentive'),
            'domain': [('id', 'in', req_ids)],
            'res_model': 'cash.incentive.head',
            'view_mode': 'tree,form',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        return action_vals

    def action_get_swift_count(self):
        all_incentive = self.env['cash.incentive.invoice'].search([('invoice_id', '=', self.id), ('swift_message_id', '!=', False)])
        req_ids = []
        for rec in all_incentive:
            req_ids.append(rec.swift_message_id.id)
        if not req_ids:
            raise UserError(_('No Swift Found.'))
        action_vals = {
            'name': _('Swift Message'),
            'domain': [('id', 'in', req_ids)],
            'res_model': 'swift.message',
            'view_mode': 'tree,form',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        return action_vals

    @api.onchange('usd_rate')
    def onchange_usd_rate(self):
        price_unit = 0
        for rec in self.invoice_line_ids:
            if rec.usd_price != 0 and self.usd_rate != 0:
                unit_price = rec.usd_price * self.usd_rate
                rec.price_unit = unit_price
                # rec.update({'price_unit': unit_price})
                # rec._onchange_product_id()
                rec._get_price_total_and_subtotal()
                rec._onchange_price_subtotal()
                self._onchange_partner_id()
            else:
                unit_price = 0
                rec.price_unit = unit_price
                # rec.update({'price_unit': unit_price})
                # rec._onchange_product_id()
                rec._get_price_total_and_subtotal()
                rec._onchange_price_subtotal()
                self._onchange_partner_id()

    @api.onchange('foreign_currency_type', 'date')
    def onchange_currency_id(self):
        for rec in self:
            rec.currency_symbol = self.foreign_currency_type.symbol
            currency_rate_obj = self.env['currency.conversion.rate'].search(
                [('date', '<=', self.date), ('currency_id', '=', self.foreign_currency_type.id), ('type', '=', '01')], order='date DESC', limit=1)
            if currency_rate_obj:
                self.usd_rate = currency_rate_obj.rate
                self.onchange_usd_rate()
            else:
                self.usd_rate = 0
                self.onchange_usd_rate()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        super(AccountMoveInheritCashIncentive, self)._onchange_partner_id()
        address = ''
        if self.partner_id.street:
            address += self.partner_id.street if not address else ', ' + self.partner_id.street
        if self.partner_id.street2:
            address += self.partner_id.street2 if not address else ', ' + self.partner_id.street2
        self.partner_address = address

    @api.onchange('contract_ids')
    def onchange_contract_ids(self):
        self._onchange_partner_id()

    def name_get(self):
        result = []
        for r in self:
            if r.ref:
                result.append((r.id, r.ref))
            else:
                result.append((r.id, r.name))
        return result

    def _compute_total_discount_amount(self):
        for rec in self:
            discount_amount = 0
            if rec.invoice_line_ids:
                for data in rec.invoice_line_ids:
                    discount_amount += data.discount_amount
                    rec.total_discount_amount = discount_amount
            else:
                rec.total_discount_amount = 0
    def _compute_total_price_amount(self):
        for rec in self:
            net_amount = 0
            if rec.invoice_line_ids:
                for data in rec.invoice_line_ids:
                    net_amount += data.net_amount
                    rec.total_price_amount = net_amount
            else:
                rec.total_price_amount = 0

    # @api.onchange('contract_ids')
    # def onchange_contract_ids(self):
    #     if len(self.contract_ids) < 1:
    #         self.update({
    #             'invoice_line_ids': None,
    #             'line_ids': None,
    #         })
    #     if self.contract_ids:
    #         self.update({
    #             'invoice_line_ids': None,
    #             'line_ids': None,
    #         })
    #         product_list = []
    #         line_ids = []
    #         for rec in self.contract_ids:
    #             for line in rec.contract_line_ids:
    #                 if line.product_id.id not in line_ids:
    #                     product_list.append((0, 0, {'product_id': line.product_id.id,
    #                                                 'quantity': line.quantity,
    #                                                 'usd_price': line.sale_price,
    #                                                 'price_unit': 0,
    #                                                 'price_total': line.total_amount,
    #                                                 'quantity_type': line.quantity_type,
    #                                                 'account_id': line.product_id.categ_id.property_account_income_categ_id.id,
    #                                                 'name': line.product_id.name,
    #                                                 'is_contact_po': True}))
    #                     line_ids.append(line.product_id.id)
    #         if product_list:
    #             self.update({'invoice_line_ids': product_list})
    #         for rec in self.invoice_line_ids:
    #             # rec._onchange_product_id()
    #             # rec._onchange_price_subtotal()
    #             rec.price_unit = 0
    #         self._onchange_partner_id()
    #         # for rec in self.line_ids:
    #         #     print(rec.account_id.name)
    #         #     print(rec.debit)
    #         #     print(rec.credit)
    #         # self._compute_total_price_amount()

    def print_foreign_invoice(self):
        contract_name = ''
        for r in self.contract_ids:
            if not contract_name:
                contract_name += r.reference
            else:
                contract_name += ', ' + r.reference
        data = {
            'contract_name': contract_name,
            'id': self.id,
        }
        return self.env.ref(
                'cash_incentive.foreign_invoice_report_id').with_context().report_action(self, data=data)

    def print_voucher(self):
        if self.journal_id.report_format == '0':
            return self.env.ref(
                'cash_incentive.journal_entry_report_id').with_context().report_action(self)
        elif self.journal_id.report_format == '1':
            return self.env.ref(
                'cash_incentive.voucher_report_id').with_context().report_action(self)
        elif self.journal_id.report_format == '2':
            return self.env.ref(
                'cash_incentive.voucher_report_id').with_context().report_action(self)
        else:
            return self.env.ref(
                'cash_incentive.journal_entry_report_id').with_context().report_action(self)


class AccountMoveLineInheritCashIncentive(models.Model):
    _inherit = 'account.move.line'

    is_contact_po = fields.Boolean(default=False)
    discount_amount = fields.Float(string='Disc. Amount', )
    net_amount = fields.Float(string='Net Total', compute='_compute_net_amount', store=True)
    discount_amount_prct = fields.Float(string='Disc. Amount')

    def _get_products(self):
        if self.env.context.get('is_service'):
            return [('type', '=', 'service'), ('sale_ok', '=', False)]

    product_id = fields.Many2one('product.product', string='Product', domain=_get_products, change_default=True)
    usd_price = fields.Float(string='Unit Rate (FC)', digits=(16, 2))
    quantity_type = fields.Selection([('0', "Hour"),
                                      ('1', "Developer")], default="0")
    qty_usd_price = fields.Float(string='Foreign Price (FC)', digits=(16, 2),compute='_compute_qty_usd_price',readonly=True, store=True, default=0)
    quantity = fields.Float(string='Quantity',
                            default=1.0,  digits=(16, 2),
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.")
    @api.onchange('usd_price', 'quantity')
    def _onchange_foreign_price(self):
        if self.usd_price != 0 and self.move_id.usd_rate != 0:
            unit_price = self.usd_price * self.move_id.usd_rate
            self.price_unit = unit_price

    @api.depends('usd_price',  'quantity')
    def _compute_qty_usd_price(self):
        for rec in self:
            sum_usd = rec.usd_price * rec.quantity
            rec.qty_usd_price = sum_usd
            rec.usd_price = rec.usd_price

    @api.depends('quantity', 'price_unit')
    def _compute_net_amount(self):
        for rec in self:
            multiply = rec.quantity * rec.price_unit
            rec.net_amount = multiply
            rec.discount_amount_prct = multiply