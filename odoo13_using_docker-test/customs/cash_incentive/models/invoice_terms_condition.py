from odoo import api, fields, models
from odoo.addons.helper import validator


class InheritCashIncentiveTANDCO(models.Model):
    _name = "invoice.terms.condition"

    name = fields.Char(string="Title", required=True, size=120, help="Title can be maximum 120 characters")
    description = fields.Html(string="Description")
    active = fields.Boolean(default=True)

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Title"
        envObj = self.env['invoice.terms.condition']
        conditionList = [('name', '=ilike', self.name), '|', ('active', '=', True), ('active', '=', False)]

        validator.check_duplicate_value(self, envObj, conditionList, msg)

    @api.constrains('description')
    def _check_termscondition_description_length(self):
        limit = 10000
        record = self.description
        field_name = "Description"
        validator._check_length_with_clean_htmltag(self, record, limit, field_name)
