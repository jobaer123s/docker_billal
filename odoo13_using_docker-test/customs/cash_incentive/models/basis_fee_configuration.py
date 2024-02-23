from odoo import models, fields, api, _, exceptions
import re


class BasisFeeConfiguration(models.Model):
    _name = "basis.fee.configuration"
    _description = "Cash Incentive Basis Fee Configuration"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', tracking=True)
    max_amount = fields.Float(string='Max Amount >', tracking=True)
    extend_amount_range = fields.Float(string='Extend Amount Range', tracking=True)
    extend_amount = fields.Float(string='Extend Amount per Range', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    basis_fee_line_ids = fields.One2many('basis.fee.configuration.line', 'head_id', string='Fee Lines', tracking=True, copy=True)

    @api.constrains('active')
    def _check_unique_amount(self):
        basis_obj = self.env['basis.fee.configuration']
        for rec in self:
            if rec.active:
                record = basis_obj.sudo().search([('id', '!=', rec.id), ('active', '=', True)], limit=1)
                if record:
                    msg = '%s ' % record.name
                    raise exceptions.ValidationError("An Active Configuration '" + msg + "' already exists! Please Inactive Or Edit that.")
    
    @api.model
    def create(self, vals):
        res = super(BasisFeeConfiguration, self).create(vals)
        if res:
            res.name = self.env['ir.sequence'].get('basis_fee_code')
        return res
    

class BasisFeeConfigurationLine(models.Model):
    _name = "basis.fee.configuration.line"

    head_id = fields.Many2one('basis.fee.configuration', ondelete='cascade')

    from_amount = fields.Float(string='From Amount <=', tracking=True)
    to_amount = fields.Float(string='To Amount >=', tracking=True)
    fee_amount = fields.Float(string='Fee Amount', tracking=True)
    sequence = fields.Integer(index=True, help="Give the sequence no.", default=1)

    @api.constrains('from_amount', 'to_amount')
    def _check_unique_amount(self):
        basis_obj = self.env['basis.fee.configuration.line']
        for rec in self:
            if rec.from_amount < 0 or rec.to_amount < 0:
                raise exceptions.ValidationError("Amount can't be negative!")
            msg = ('%s and %s' % (rec.from_amount, rec.to_amount))
            record = basis_obj.sudo().search(
                [('id', '!=', rec.id),('head_id', '=', rec.head_id.id), ('from_amount', '=', rec.from_amount), ('to_amount', '=', rec.to_amount)],
                limit=1)
            print('record', record)
            if record:
                raise exceptions.ValidationError("'" + msg + "' already exists!")