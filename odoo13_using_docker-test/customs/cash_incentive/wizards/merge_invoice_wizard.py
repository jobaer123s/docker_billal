from odoo import models, fields, _, api
from odoo.exceptions import AccessError
import datetime
import math


class MergeInvoiceWizard(models.TransientModel):
    _name = 'invoice.merge.auto'
    _description = 'Merge Req Wizard'

    file_id = fields.Many2one('cash.incentive.head', string='File')
    partner_id = fields.Many2one('res.partner', string='Customer')
    swift_customer_name = fields.Char(string='SWIFT Customer Name')
    state = fields.Selection([
        ('01', 'Create New File'),
        ('02', 'Assign File')
    ], string='Type', copy=False, default='01')
    name = fields.Char(string='Reference',  tracking=2)
    bank_id = fields.Many2one('res.bank', string='Bank', tracking=17, domain="[('is_cash_incentive_bank', '=', True)]")
    customer_address = fields.Text(tracking=14)
    institution_address = fields.Text(tracking=15)
    date = fields.Date(string='Preparation Date', default=fields.Date.context_today, tracking=3)
    application_deadline = fields.Date(string='Application Deadline', tracking=5,
                                       help='Application Deadline Will be 179 Days More than SWIFT Date')
    remaining_days = fields.Integer(string='Remaining days', compute='_compute_remaining_day', tracking=6)
    swift_date = fields.Date(string='Min SWIFT Date')
    basis_fee_amt = fields.Float(string='BASIS Fee (BDT)')
    invoice_line_ids = fields.One2many('invoice.merge.auto.line', 'head_id', string='Invoices', tracking=18)

    @api.onchange('bank_id')
    def on_change_bank_id(self):
        if self.bank_id:
            m_code_id = self.env['cash.incentive.head'].search([('bank_id', '=', self.bank_id.id)], limit=1, order="id DESC")
            m_code = m_code_id.name if m_code_id else ''
            if not m_code_id:
                if self.bank_id.code_prefix:
                    m_code = str(self.bank_id.code_prefix).strip()
                if self.bank_id.code_suffix:
                    if m_code:
                        m_code = m_code + str(self.bank_id.code_suffix)
                    else:
                        m_code = str(self.bank_id.code_suffix).strip()
            self.name = m_code

    @api.depends("application_deadline")
    def _compute_remaining_day(self):
        for rec in self:
            today = fields.Date.today()
            application_deadline = rec.application_deadline
            remaining_days=0
            if today and application_deadline:
                try:
                    remaining_days = (application_deadline - today).days
                except:
                    remaining_days = 0
            rec.remaining_days = remaining_days

    @api.onchange('inv_ids')
    def on_change_inv_ids(self):
        basis_fee_amt = sum(self.inv_ids.mapped('invoice_amt'))
        if basis_fee_amt < 5001:
            self.basis_fee_amt = 850
        if basis_fee_amt > 5000 and basis_fee_amt < 10001:
            self.basis_fee_amt = 1600
        if basis_fee_amt > 10000 and basis_fee_amt < 30001:
            self.basis_fee_amt = 3100
        if basis_fee_amt > 30000 and basis_fee_amt < 50001:
            self.basis_fee_amt = 6200
        if basis_fee_amt > 50000 and basis_fee_amt < 80001:
            self.basis_fee_amt = 12100
        if basis_fee_amt > 80000 and basis_fee_amt < 120001:
            self.basis_fee_amt = 24100
        if basis_fee_amt > 120000:
            a = basis_fee_amt - 120000
            if a > 50000:
                b = a / 50000
                truncA = math.trunc(b)
                c = truncA * 3000
                self.basis_fee_amt = 24100 + c

    @api.model
    def default_get(self, fields):
        res = super(MergeInvoiceWizard, self).default_get(fields)
        application_deadline = []
        swift_date = []
        active_ids = self.env.context.get('active_ids')
        partners = []
        banks = []
        invoices = []
        basis_fee_amt = 0
        invoice_line1 = []
        model_name = self.env.context.get('model_name')
        if model_name == 'swift':

            invoice_ids = self.env['cash.incentive.invoice'].search([('swift_message_id', 'in', active_ids)]).ids
            if not invoice_ids:
                raise AccessError(
                    _("Warning! One of the SWIFT has no Invoice.")
                )
            for x in active_ids:
                swift_obj = self.env['swift.message'].sudo().browse(x)
                if swift_obj.bank_id.id not in banks:
                    banks.append(swift_obj.bank_id.id)
            # invoice_ids = [x.id for x in swift_ids]
        else:
            invoice_ids = active_ids
        for data in invoice_ids:
            inv_obj = self.env['cash.incentive.invoice'].sudo().browse(data)
            qty = ''
            h_q = 0
            d_q = 0
            for l in inv_obj.invoice_id.invoice_line_ids:
                if l.quantity_type == '0':
                    h_q += l.quantity
                else:
                    d_q += l.quantity
            if h_q:
                if not qty:
                    qty += 'ITES/' + str(h_q) + ' hrs'
                else:
                    qty += ', ITES/' + str(h_q) + ' hrs'
            if d_q:
                if not qty:
                    qty += 'ITES/' + str(d_q) + ' Developers' if d_q > 1 else 'ITES/' + str(d_q) + ' Developer'
                else:
                    qty += ', ITES/' + str(d_q) + ' Developers' if d_q > 1 else ', ITES/' + str(d_q) + ' Developer'

            moveLineData4 = {
                'in_invoice_id': inv_obj.id,
                'file_id': inv_obj.head_id.id,
                'invoice_id': inv_obj.invoice_id.id,
                'invoice_date': inv_obj.invoice_date,
                'swift_date': inv_obj.swift_date,
                'encashment_date': inv_obj.encashment_date,
                'currency_id': inv_obj.currency_id.id,
                'invoice_amt': inv_obj.invoice_amt,
                'usd_rate': inv_obj.usd_rate,
                'swift_customer_name': inv_obj.swift_customer_name,
                'invoice_qty_str': qty,
                'invoice_amt_bdt': inv_obj.invoice_amt_bdt,
                'swift_amt': inv_obj.swift_amt,
                'od_sight_rate': inv_obj.od_sight_rate,
                'encashment_rate_bdt': inv_obj.encashment_rate_bdt,
                'incentive_amt_fc': inv_obj.incentive_amt_fc,
                'incentive_amt_bdt': inv_obj.incentive_amt_bdt,
                'encashment_amt_bdt': inv_obj.encashment_amt_bdt,
            }
            invoice_line1.append((0, 0, moveLineData4))
            
            basis_fee_amt += inv_obj.invoice_amt
            if inv_obj.application_deadline:
                application_deadline.append(inv_obj.application_deadline)

            if inv_obj.swift_date:
                swift_date.append(inv_obj.swift_date)

            if inv_obj.partner_id.id not in partners:
                partners.append(inv_obj.partner_id.id)
            if inv_obj.bank_id.id not in banks:
                banks.append(inv_obj.bank_id.id)

            if model_name != 'swift':
                if inv_obj.head_id:
                    raise AccessError(
                        _("Warning! %s This Invoice has already a file." %inv_obj.invoice_id.ref)
                    )
                
                if not inv_obj.swift_message_id:
                    raise AccessError(
                        _("Warning! %s This Invoice has no SWIFT." %inv_obj.invoice_id.ref)
                    )

                if inv_obj.invoice_id.id in invoices:
                    raise AccessError(
                        _("Warning! Same Invoice is not allowed.")
                    )
                else:
                    invoices.append(inv_obj.invoice_id.id)
        if basis_fee_amt < 5001:
            res['basis_fee_amt'] = 850
        if basis_fee_amt > 5000 and basis_fee_amt < 10001:
            res['basis_fee_amt'] = 1600
        if basis_fee_amt > 10000 and basis_fee_amt < 30001:
            res['basis_fee_amt'] = 3100
        if basis_fee_amt > 30000 and basis_fee_amt < 50001:
            res['basis_fee_amt'] = 6200
        if basis_fee_amt > 50000 and basis_fee_amt < 80001:
            res['basis_fee_amt'] = 12100
        if basis_fee_amt > 80000 and basis_fee_amt < 120001:
            res['basis_fee_amt'] = 24100
        if basis_fee_amt > 120000:
            a = basis_fee_amt - 120000
            if a > 50000:
                b = a / 50000
                truncA = math.trunc(b)
                c = truncA * 3000
                res['basis_fee_amt'] = 24100 + c
        if application_deadline:
            min_application_deadline = min(application_deadline)
            res['application_deadline'] = min_application_deadline
        else:
            res['application_deadline'] = None
        if swift_date:
            z = min(swift_date)
            res['swift_date'] = z
        else:
            res['swift_date'] = None
        #print(partners)
        if len(partners) > 1:
            raise AccessError(
                _("Warning! Different Customer is Not Allowed.")
            )
        if len(banks) > 1:
            raise AccessError(
                _("Warning! Different Bank is Not Allowed.")
            )
        if partners:
            res['partner_id'] = partners[0]
            #res['swift_customer_name'] = partners[0]

        if banks:
            res['bank_id'] = banks[0]
        if active_ids:
            # res['inv_ids'] = [(6, 0, active_ids)]
            res['invoice_line_ids'] = invoice_line1
        return res
    inv_ids = fields.Many2many('cash.incentive.invoice', string='Contacts')

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        if self.partner_id:
            street = self.partner_id.street
            street2 = self.partner_id.street2
            city = self.partner_id.city
            state = self.partner_id.state_id.name if self.partner_id.state_id else ''
            zip = self.partner_id.zip
            country = self.partner_id.country_id.name if self.partner_id.country_id else ''

            address = ''
            if street:
                address = street
            if street2:
                if address:
                    address += ', ' + street2
                else:
                    address = street2
            if city:
                if address:
                    address += ', ' + city
                else:
                    address = city
            if state:
                if address:
                    address += ', ' + state
                else:
                    address = state
            if zip:
                if address:
                    address += ', ' + zip
                else:
                    address = zip
            if country:
                if address:
                    address += ', ' + country
                else:
                    address = country

            self.customer_address = address
            self.institution_address = address

        else:
            self.customer_address = ''
            self.institution_address = ''

    def action_assign(self):
        model_name = self.env.context.get('model_name')
        if model_name == 'swift':
            if any(cid.in_invoice_id.head_id for cid in self.invoice_line_ids):
                raise AccessError(
                    _("Warning! One of the Invoice has already a file.")
                )
            inv_partners = []
            for invp in self.invoice_line_ids:
                inv_partners.append(invp.in_invoice_id.partner_id.id or None)
            if self.partner_id.id not in inv_partners:
                raise AccessError(
                    _("Warning! Customer can not be changed!")
                )

        for rec in self.invoice_line_ids:
            rec.in_invoice_id.head_id = self.file_id.id
            if rec.swift_customer_name:
                self.file_id.swift_customer_name = rec.swift_customer_name
            rec.invoice_id.cash_incentive_id = self.file_id.id
            qty = ''
            h_q = 0
            d_q = 0
            for l in rec.invoice_id.invoice_line_ids:
                if l.quantity_type == '0':
                    h_q += l.quantity
                else:
                    d_q += l.quantity
            if h_q:
                if not qty:
                    qty += 'ITES/' + str(h_q) + ' hrs'
                else:
                    qty += ', ITES/' + str(h_q) + ' hrs'
            if d_q:
                if not qty:
                    qty += 'ITES/' + str(d_q) + ' Developers' if d_q > 1 else 'ITES/' + str(d_q) + ' Developer'
                else:
                    qty += ', ITES/' + str(d_q) + ' Developers' if d_q > 1 else ', ITES/' + str(d_q) + ' Developer'
            rec.in_invoice_id.invoice_qty_str = qty
            rec.in_invoice_id.head_id.on_change_invoice_line_ids()
            rec.in_invoice_id.onchange_swift_message_id()

        action_vals = {
            'name': _('Cash Incentive'),
            'domain': [('id', 'in', self.file_id.id)],
            'res_model': 'cash.incentive.head',
            'view_id': False,
            'res_id': self.file_id.id,
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
        }
        return action_vals

    def action_create(self):
        model_name = self.env.context.get('model_name')
        if model_name == 'swift':
            if any(cid.in_invoice_id.head_id for cid in self.invoice_line_ids):
                raise AccessError(
                    _("Warning! One of the Invoice has already a file.")
                )
            inv_partners = []
            for invp in self.invoice_line_ids:
                inv_partners.append(invp.in_invoice_id.partner_id.id or None)
            if self.partner_id.id not in inv_partners:
                raise AccessError(
                    _("Warning! Customer can not be changed!")
                )

        head_code = self.name
        file_obj = self.env['cash.incentive.head'].create({
            'state': 'draft',
            'name': head_code,
            'bank_id': self.bank_id.id,
            'customer_address': self.customer_address,
            'institution_address': self.institution_address,
            'date': self.date,
            'application_deadline': self.application_deadline,
            'remaining_days': self.remaining_days,
            'partner_id': self.partner_id.id,
            'customer_country_id': self.partner_id.country_id.id if self.partner_id.country_id else None,
            'fc_currency_id': None,
        })
        file_obj.on_change_bank_ref()

        fileId = file_obj['id']
        fc_currency_id = None
        swift_message_ids = []

        for rec in self.invoice_line_ids:
            if rec.swift_customer_name:
                file_obj.swift_customer_name = rec.swift_customer_name
            rec.invoice_id.cash_incentive_id = fileId
            rec.in_invoice_id.head_id = fileId
            rec.in_invoice_id.invoice_qty_str = rec.invoice_qty_str
            rec.in_invoice_id.od_sight_rate = rec.od_sight_rate
            rec.in_invoice_id.incentive_amt_bdt = rec.incentive_amt_bdt
            rec.in_invoice_id.head_id.on_change_invoice_line_ids()
            rec.in_invoice_id.onchange_swift_message_id()
            # rec.in_invoice_id.onchange_invoice_id()



            if rec.in_invoice_id.swift_message_id:
                if not fc_currency_id:
                    fc_currency_id = rec.in_invoice_id.swift_message_id.currency_id.id if rec.in_invoice_id.swift_message_id.currency_id else None
                if rec.in_invoice_id.swift_message_id.id not in swift_message_ids:
                    swift_message_ids.append(rec.in_invoice_id.swift_message_id.id)



        if fc_currency_id:
            file_obj['fc_currency_id'] = fc_currency_id
        if len(swift_message_ids)>0:
            file_obj['swift_ids'] = swift_message_ids


            # file_obj.on_change_invoice_line_ids()
        action_vals = {
            'name': _('Cash Incentive'),
            'domain': [('id', 'in', fileId)],
            'res_model': 'cash.incentive.head',
            'view_id': False,
            'res_id': fileId,
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
        }
        return action_vals


class MergeInvoiceWizardLine(models.TransientModel):
    _name = "invoice.merge.auto.line"

    head_id = fields.Many2one('invoice.merge.auto', ondelete='cascade')
    in_invoice_id = fields.Many2one('cash.incentive.invoice', string='Invoices', ondelete='cascade')
    file_id = fields.Many2one('cash.incentive.head', string='File', ondelete='cascade')

    invoice_id = fields.Many2one('account.move', string='Invoices', ondelete='cascade')
    invoice_date = fields.Date(string='Invoice Date')
    swift_date = fields.Date(string='SWIFT Date')
    encashment_date = fields.Date(string='Encashment Date')

    invoice_qty_str = fields.Char(string='Quantity')
    swift_customer_name = fields.Char(string='SWIFT Customer Name')
    invoice_amt = fields.Float(string='Invoice Amount')
    basis_fee_amt = fields.Float(string='Basis Fee Amount')
    swift_amt = fields.Float(string='Swift Amount')
    currency_id = fields.Many2one("res.currency", string="Currency")

    incentive_amt_fc = fields.Float(string='Incentive Amount (FC)', digits=(16, 2))
    incentive_amt_bdt = fields.Float(string='Incentive Amount (BDT)', compute='_compute_incentive_amt_bdt')
    encashment_amt_bdt = fields.Float(string='Equivalent Amount (BDT)', digits=(16, 2),)
    contract_number = fields.Char(string='Contract No.')
    contract_date_str = fields.Char(string='Contract Date')

    od_sight_rate = fields.Float(string='OD Sight Rate', digits=(16, 4) )
    incentive_rate_fc = fields.Float(string='Incentive Rate (FC)(%)', digits=(16, 2), default=10)
    encashment_rate_bdt = fields.Float(string='Encashment Rate (BDT)', digits=(16, 4))

    application_deadline = fields.Date(string='Application Deadline', tracking=5,
                                       help='Application Deadline Will be 179 Days More than SWIFT Date',)
    swift_date = fields.Date(string='SWIFT Date')
    remaining_days = fields.Integer(string='Remaining days',  tracking=6)

    # -----------
    usd_rate = fields.Float(string='Invoice BDT Rate', digits=(16, 3), related='invoice_id.usd_rate')


    difference_amnt_bdt = fields.Float(string='Difference Amount (BDT)', digits=(16, 2))

    invoice_amt_bdt = fields.Float(string='Invoice Amount (BDT)', digits=(16, 2))

    @api.depends("od_sight_rate", "incentive_amt_fc")
    def _compute_incentive_amt_bdt(self):
        for rec in self:
            incentive_amt_bdt = 0
            if rec.od_sight_rate > 0 and rec.incentive_amt_fc > 0:
                try:
                    incentive_amt_bdt = round((rec.od_sight_rate * rec.incentive_amt_fc), 2)
                except:
                    incentive_amt_bdt = 0
            rec.incentive_amt_bdt = incentive_amt_bdt