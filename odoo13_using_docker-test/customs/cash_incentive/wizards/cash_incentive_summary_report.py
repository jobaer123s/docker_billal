from odoo import models, fields, _, api
from odoo.exceptions import AccessError, UserError, ValidationError
import datetime
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO


class CashIncentiveExcelWizard(models.TransientModel):

    _name = 'cash.incentive.excel.print.wizards'

    file_data = fields.Binary(' Report')
    start_date = fields.Date(string='SWIFT Start Date')
    end_date = fields.Date(string='SWIFT End Date')
    type = fields.Selection([
        ('01', 'All'),
        ('02', 'Specific')
    ], string='Bank', copy=False, default='01')
    bank_id = fields.Many2one('res.bank', string='Bank', domain="[('is_cash_incentive_bank', '=', True)]", tracking=17)

    @api.onchange('type')
    def on_change_type(self):
        if self.type:
            self.bank_id = None

    def date_constrains(self, start_date, end_date):
        if (not start_date and end_date) or (start_date and not end_date):
            raise ValidationError(_('Start date and end date both should be filled up.'))
        if start_date > end_date:
            raise ValidationError(_('Start date cannot be greater than the end date.'))

        return [start_date, end_date]

    def incentive_report_excel(self):
        date = self.date_constrains(self.start_date, self.end_date)
        start_date = date[0]
        end_date = date[1]
        # date = self.date_constrains(self.start_date, self.end_date)
        file_name = "Cash Incentive Summary Report.xlsx"
        file_pointer = BytesIO()
        workbook = xlsxwriter.Workbook(file_pointer)
        # main header formatting
        format0 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format0.set_align('center')
        format0.set_border()

        # column header formatting
        format1 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format1.set_align('left')
        format1.set_border()
        format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format2.set_align('center')
        format2.set_border()
        format3 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format3.set_align('right')
        format3.set_border()

        # body formatting
        format4 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format4.set_align('left')
        format4.set_border()
        format5 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format5.set_align('center')
        format5.set_border()
        format10 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format10.set_align('left')
        format10.set_border()
        format9 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format9.set_align('right')
        format9.set_border()
        format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
        format8.set_align('left')
        format8.set_border()
        format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format6.set_align('right')
        format6.set_border()
        format7 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format7.set_border()
        format7.set_align('center')

        sheet = workbook.add_worksheet('Cash Incentive Summary Report')

        sheet.merge_range(0, 0, 0, 6, "Cash Incentive Summary Report", format0)

        h_col = 0
        sheet.write(1, h_col, 'Sl No.', format7)
        h_col += 1
        sheet.write(1, h_col, 'File Reference No.', format8)
        h_col += 1
        sheet.write(1, h_col, 'Name of Client', format8)
        h_col += 1
        sheet.write(1, h_col, 'Export Contract No.', format8)
        h_col += 1
        sheet.write(1, h_col, 'Contract Date', format8)
        h_col += 1
        # sheet.write(3, 2, 'Joining Date', format2)

        sheet.write(1, h_col, 'Invoice Amount', format1)
        h_col += 1
        sheet.write(1, h_col, 'Currency', format8)

        row = 2
        col = 0
        search_domain = []
        if self.start_date and self.end_date:
            search_domain.append(('swift_message_id.date', '>=', self.start_date))
            search_domain.append(('swift_message_id.date', '<=', self.end_date))

        incentive_obj1 = self.env['cash.incentive.invoice'].search(search_domain, order='id asc')
        file_ids_list = []
        if incentive_obj1:
            for rec in incentive_obj1:
                if rec.head_id:
                    file_ids_list.append(rec.head_id.id)

        file_ids = list(set(file_ids_list))
        search_domain1 = [('state', '!=', 'cancel')]
        if file_ids:
            search_domain1.append(('id', 'in', file_ids))
        if self.bank_id:
            search_domain1.append(('bank_id', '=', self.bank_id.id))

        incentive_obj = self.env['cash.incentive.head'].search(search_domain1, order='name asc')

        total_invoice_amt = 0
        sl_no = 1
        for line in incentive_obj:
            con_no = ''
            if line.contract_number:
                con_no = line.contract_number.replace('Contract No.', '').replace('Purchase Order No.', '')

            inv_list = []
            invoice_amt = 0
            for inv in line.invoice_line_ids:
                inv_id = inv.invoice_id.id
                if inv_id not in inv_list:
                    inv_list.append(inv_id)
                    invoice_amt += inv.invoice_amt

            #invoice_amt = sum(line.invoice_line_ids.mapped('invoice_amt'))
            t_col = 0
            sheet.write(row, col + t_col, sl_no, format5)
            t_col += 1
            sheet.write(row, col + t_col, line.name, format4)
            t_col += 1
            sheet.write(row, col + t_col, line.swift_customer_name if line.swift_customer_name else '', format4)
            t_col += 1
            sheet.write(row, col + t_col, con_no if line.contract_number else '', format4)
            t_col += 1
            sheet.write(row, col + t_col, line.contract_date_str if line.contract_date_str else '', format4)
            t_col += 1
            sheet.write(row, col + t_col, str("{:,.2f}".format(invoice_amt)), format9)
            t_col += 1
            total_invoice_amt += invoice_amt
            sheet.write(row, col + t_col, line.fc_currency_id.name if line.fc_currency_id else '', format4)
            t_col += 1

            row = row + 1
            sl_no = sl_no + 1

        sheet.merge_range(row, 0, row, 4, "Total", format6)
        sheet.write(row, 5, str("{:,.2f}".format(total_invoice_amt)), format6)
        sheet.write(row, 6, '', format6)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Cash Incentive Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=cash.incentive.excel.print.wizards&field=file_data&filename={}&id={}'.format(file_name ,self.id),
            'target': 'self',
        }