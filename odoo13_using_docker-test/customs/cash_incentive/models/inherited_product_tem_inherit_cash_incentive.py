from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ProductTemplateCashIncentive(models.Model):
    _inherit = "product.template"

    is_default_invoice_product = fields.Boolean(string='Is Default Invoice Product?', default=False)
    is_default_discount_product = fields.Boolean(string='Is Default Discount Product?', default=False)