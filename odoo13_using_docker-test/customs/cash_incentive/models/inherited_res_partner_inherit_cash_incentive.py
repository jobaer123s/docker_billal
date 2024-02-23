from datetime import date, timedelta
from odoo import fields, models, api, _
from odoo import exceptions


class InheritedResPartnerTOCashIncentive(models.Model):
    _inherit = "res.partner"

    vendor_type = fields.Selection([
        ('local', 'LOCAL'),
        ('foreign', 'FOREIGN')
    ], string='Local/Foreign', default='local', copy=False)
    division_id = fields.Many2one("division", string="Division")
    categ_id = fields.Many2one('customer.category', 'Customer Category', ondelete='cascade',
                               default=lambda self: self.__def_categ_id())
    postcode_id = fields.Many2one("postcode", string="Postcode")
    thana_id = fields.Many2one("district.thana", string="Upazila/Thana")
    district_id = fields.Many2one("district", string="District")
    mobile_customer_type = fields.Selection([
        ('retail', 'Retail Customer'),
        ('distributor', 'Distributor/Reseller'),
        ('corporate', 'Corporate Customer'),
        ('vendor', 'Vendor/Supplier'),
        ('special', 'Special Discount')], string='Type', default='retail',
        required=True)
    partner_code = fields.Char(string='Partner Code', default='')

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            # if record.country_id:
            #     name = "%s [%s]" % (name, record.country_id.name)
            if record.is_employee and record.employee_id:
                name = "%s [%s]" % (name, record.employee_id)

            result.append((record.id, name))
        return result

    @api.model
    def __def_categ_id(self):
        terms_cond = self.env['customer.category'].search([('id', '!=', False)], order="sequence asc", limit=1)
        if terms_cond:
            return terms_cond.id
        else:
            return ''

    @api.model
    def create(self, vals):
        res = super(InheritedResPartnerTOCashIncentive, self).create(vals)
        if len(vals) <= 2:
            raise exceptions.ValidationError(_('Too few information to create a customer'))
        for rec in res:
            if rec.mobile_customer_type == 'vendor':
                if rec.supplier_rank in (0, ''):
                    rec.customer_rank = 0
                    rec.supplier_rank = 1

                partner_code = self.env['ir.sequence'].get('vendor_code')
                rec.partner_code = partner_code
                rec.vendor_code = partner_code

            else:
                if rec.customer_rank in (0, ''):
                    rec.customer_rank = 1
                    rec.supplier_rank = 0
                # -----------
                partner_code = ''
                if rec.mobile_customer_type == 'retail':
                    partner_code = self.env['ir.sequence'].get('retail_cust_code')
                elif rec.mobile_customer_type == 'distributor':
                    partner_code = self.env['ir.sequence'].get('distributor_cust_code')
                elif rec.mobile_customer_type == 'corporate':
                    partner_code = self.env['ir.sequence'].get('corporate_cust_code')
                elif rec.mobile_customer_type == 'special':
                    partner_code = self.env['ir.sequence'].get('special_cust_code')
                else:
                    pass
                rec.partner_code = partner_code

        return res

    def write(self, vals):
        prev_type = self.mobile_customer_type
        prev_code = self.partner_code

        res = super(InheritedResPartnerTOCashIncentive, self).write(vals)
        # for rec in self:
        new_type = self.mobile_customer_type

        if self.mobile_customer_type == 'vendor':
            if self.supplier_rank in (0, ''):
                self.supplier_rank = 1
                self.customer_rank = 0

            if prev_type != new_type:
                partner_code = self.env['ir.sequence'].get('vendor_code')
                self.partner_code = partner_code
                self.vendor_code = partner_code
        else:
            if self.customer_rank in (0, ''):
                self.customer_rank = 1
                self.supplier_rank = 0

            # -----------
            if prev_type != new_type or prev_code == '' or prev_code == None:
                partner_code = self.partner_code
                if new_type == 'retail':
                    partner_code = self.env['ir.sequence'].get('retail_cust_code')
                elif new_type == 'distributor':
                    partner_code = self.env['ir.sequence'].get('distributor_cust_code')
                elif new_type == 'corporate':
                    partner_code = self.env['ir.sequence'].get('corporate_cust_code')
                elif new_type == 'special':
                    partner_code = self.env['ir.sequence'].get('special_cust_code')
                else:
                    pass
                self.partner_code = partner_code

        return res
