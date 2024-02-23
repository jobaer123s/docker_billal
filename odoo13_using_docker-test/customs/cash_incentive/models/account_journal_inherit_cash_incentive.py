from odoo import fields, models, api


class InheritedAccountJournalInheritDaybook(models.Model):
    _inherit = "account.journal"
    _description = "Inherited Account Journal Inherit Daybook"

    report_format = fields.Selection([
        ('0', 'Default'),
        ('1', 'Print as Payment Voucher'),
        ('2', 'Print as Receipt Voucher'),
        ('3', 'Print as Contra Voucher'),
        ('4', 'Print as Journal Voucher'),
        ('5', 'Print as Salary Voucher')
    ], string='Report Format', default='0')
