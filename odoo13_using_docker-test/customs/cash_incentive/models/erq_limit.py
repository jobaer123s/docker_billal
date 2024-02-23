from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError


class ERQLimit(models.Model):
    _name = "erq.limit"

    date = fields.Date(string='SWIFT Date', required=True, default=fields.Date.context_today)
    limit = fields.Float(string='Limit')

    @api.onchange('limit')
    def on_change_tenor_date(self):
        if self.limit:
            if self.limit > 100:
                raise UserError(_('Limit can not be more than 100.'))
            if self.limit < 1:
                raise UserError(_('Limit can not be less than 1.'))