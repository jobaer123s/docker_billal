from odoo import models, fields, api, _, exceptions
import re
import datetime
from odoo.exceptions import UserError
from odoo.addons.helper import validator
from dateutil.relativedelta import relativedelta


class ClientContract(models.Model):
    _name = "client.contract"
    _description = "Client Contract"
    _rec_name = "reference"
    _order = "id desc"

    code = fields.Char(string='ERP Code')
    reference = fields.Char(string='Reference', required=True)
    type = fields.Selection([('0', "Contract"), ('1', "PO"), ('2', "Work Order")], default="0", required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, domain="[('type', '=', 'contact'), ('active', '=', True), ('customer_rank', '>', 0)]")
    swift_customer_name = fields.Char(string='SWIFT Customer Name', tracking=13)
    date = fields.Date(string='Contract Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='Contract End Date')
    other_details = fields.Text(string='Other Details')
    range = fields.Char(string='Range/Price')
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, default='draft')
    length_of_year = fields.Char(string='Tenor', compute='_compute_tenor_length')

    tenor_year = fields.Selection([
        ('1', 1),
        ('2', 2),
        ('3', 3),
        ('4', 4),
        ('5', 5),
        ('6', 6),
        ('7', 7),
        ('8', 8),
        ('9', 9),
        ('10', 10),
        ('11', 11),
        ('12', 12),
        ('13', 13),
        ('14', 14),
        ('15', 15),
        ('16', 16),
        ('17', 17),
        ('18', 19),
        ('20', 20)
    ], string='Tenor(Year)', copy=False)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(string='Company Currency', readonly=True, related='company_id.currency_id')
    total_amount = fields.Monetary(string='Total Amount', store=True, readonly=True,
                                   currency_field='company_currency_id', default=0)
    is_code_change = fields.Boolean(default=False)
    contract_line_ids = fields.One2many('client.contract.line', 'head_id', string='Product')
    contract_file = fields.Binary(string='Contract File', attachment=True)
    contract_file_name = fields.Char("File Name")

    @api.depends('date','end_date')
    def _compute_tenor_length(self):
        for record in self:
            if record.end_date and record.date and record.end_date >= record.date:
                date_diff = relativedelta(
                    fields.Date.from_string(record.end_date),
                    fields.Date.from_string(record.date))
                record.length_of_year = "{y} years, {m} months, {d} days".format(y=date_diff.years,
                                                                                    m=date_diff.months, d=date_diff.days
                                                                                    )
            else:
                record.length_of_year = 'Continuing'

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.swift_customer_name = self.partner_id.name

    def save_data(self):
        return {'type': 'ir.actions.act_window_close'}

                # @api.constrains('code')
    # def _check_unique_code(self):
    #     envobj = self.env['client.contract']
    #     for rec in self:
    #         msg = '"%s"' % rec.code
    #         record = envobj.sudo().search([('id', '!=', rec.id), ('code', '=', rec.code)], limit=1)
    #         if record:
    #             raise exceptions.ValidationError("'" + msg + "' already exists!")

    def write(self, vals):
        super(ClientContract, self).write(vals)
        all_files = self.env['cash.incentive.head'].search([('contract_id', '=', self.id)])
        if all_files:
            for rec in all_files:
                # rec.contract_id_change(self.id)
                # rec.write({'contract_id' : self.id})
                for x in rec.invoice_line_ids:
                    x.contract_id = self.id
                    x.contract_number = self.code
                    date_str = datetime.datetime.strptime(str(self.date), '%Y-%m-%d').strftime('%d/%m/%y')
                    x.contract_price_str = self.range
                    x.contract_date_str = date_str
                    contract_ids = [y.id for y in self]
                    x.invoice_id.contract_ids = contract_ids
                    return

    @api.onchange('date', 'tenor_year')
    def on_change_tenor_date(self):
        if self.date and self.tenor_year:
            ten = dict(self._fields['tenor_year'].selection).get(self.tenor_year)
            ten_yr = ten * 365
            self.end_date = self.date + datetime.timedelta(days=ten_yr)

    @api.onchange('contract_line_ids')
    def _onchange_contract_line_ids(self):
        if len(self.contract_line_ids) < 1:
            self.update({
                'total_amount': 0
            })
        else:
            total_amount = 0
            for rec in self.contract_line_ids:
                total_amount += rec.total_amount
            self.update({
                'total_amount': total_amount,
            })

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        for rec in self:
            if len(rec.contract_line_ids) < 1:
                raise UserError(_("Warning! No Product line!."))
            if rec.type == '0' and not self.is_code_change:
                rec.code = self.env['ir.sequence'].get('client_contract_code')
            elif rec.type == '1' and not self.is_code_change:
                rec.code = self.env['ir.sequence'].get('client_po_code')
            elif rec.type == '2' and not self.is_code_change:
                rec.code = self.env['ir.sequence'].get('client_wo_code')
            rec.state = 'confirm'
            rec.is_code_change = True

    def action_approve(self):
        self.state = 'approve'

    def action_cancel(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only Draft record can be cancelled!.'))
            else:
                self.state = 'cancel'


class ClientContractLine(models.Model):
    _name = "client.contract.line"
    _description = "Client Contract Line"

    head_id = fields.Many2one('client.contract', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, domain="[('type', '=', 'service')]")
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='UOM', store=True, readonly=1)
    quantity_type = fields.Selection([('0', "Hour"),
                                      ('1', "Developer")], default="0")
    quantity = fields.Float(string='Quantity')
    sale_price = fields.Float()
    total_amount = fields.Float(string='Total Amount')

    @api.constrains('quantity', 'sale_price', 'head_id', 'product_id')
    def _check_quantity_sale_price(self):
        for rec in self:
            if rec.quantity < 1 or rec.sale_price < 1:
                raise UserError(_('Qty or Sale Price can not be negative!.'))

            # envobj = self.env['client.contract.line']
            # msg = 'Name "%s"' % rec.product_id.name
            # conditionlist = [('product_id', '=', rec.product_id.id),('head_id', '=', rec.head_id.id)]
            # validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.onchange('quantity', 'sale_price')
    def _onchange_sale_quantity_price(self):
        if self.quantity and self.sale_price:
            self.total_amount = self.quantity * self.sale_price

