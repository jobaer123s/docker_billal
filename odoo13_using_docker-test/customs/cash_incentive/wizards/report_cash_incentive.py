
import datetime
from odoo import fields, models, api, _
from itertools import groupby
from calendar import monthrange
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
# from datetime import datetime


try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO


class IncentiveReportWizard(models.TransientModel):
    _name = "cash.incentive.wizard"
    _description = "Cash Incentive Report Wizard"

    file_data = fields.Binary(' Report')
    partner_id = fields.Many2one('res.partner', string='Customer', domain="[('type', '=', 'contact'), ('active', '=', True), ('customer_rank', '>', 0)]")
    reference = fields.Many2one('cash.incentive.head')
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', default=fields.Date.context_today)

    @api.onchange('partner_id')
    def _get_reference(self):
        for rec in self:
            if self.partner_id:
                return {'domain': {'reference': [('partner_id', '=', rec.partner_id.id)]},
                        'value': {'reference': False}}
            else:
                return {'domain': {'reference': []},
                        'value': {'reference': False}}

    def date_constrains(self, start_date, end_date):
        if start_date > end_date:
            raise ValidationError(_('Start date cannot be greater than the end date.'))

        return [start_date, end_date]

    def incentive_report_pdf(self):
        search_domain = [('state', '!=', 'cancel'),
                         ('date', '>=', self.start_date),
                         ('date', '<=', self.end_date)]
        if self.reference:
            search_domain.append(('id', '=', self.reference.id))
        if self.partner_id:
            search_domain.append(('partner_id', '=', self.partner_id.id))

        incentive_obj = self.env['cash.incentive.head'].search(search_domain, order='id asc').ids
        # data_list = []
        # for rec in incentive_obj:
        #     data_list.append({'req_no': rec['name'],
        #                       'qty': rec['demand_qty'],
        #                       'po_qty': product_domain.product_qty,
        #                       'received_qty': product_domain.qty_received,
        #                       'remaining_qty': product_domain.product_qty - product_domain.qty_received,
        #                       'issued_qty': rec['issued_qty'] if rec['issued_qty'] else 0,
        #                       'purchase_ref': rec['po_name']
        #                       })
        data = {
            'model': 'cash.incentive.wizard',
            'form': self.read()[0],
            'csr': incentive_obj,
            'start_date': self.start_date,
            'end_date': self.end_date,
        }

        return self.env.ref('cash_incentive.incentive_report_pdf').with_context(
            landscape=True).report_action(self, data=data)

    def incentive_report_excel(self):
        date = self.date_constrains(self.start_date, self.end_date)
        start_date = date[0]
        end_date = date[1]
        # data = self.cash_incentive_report_sql(start_date, end_date)
        # file_name = "Employee Salary Sheet (%s - %s).xlsx" % (data['month'], data['year'])
        file_name = "Cash Incentive Report.xlsx"
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
        format8 = workbook.add_format({'font_size': 10, 'align': 'left','bold': True})
        format8.set_align('left')
        format8.set_border()
        format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format6.set_align('right')
        format6.set_border()
        format7 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format7.set_border()
        format7.set_align('center')

        sheet = workbook.add_worksheet('Cash Incentive Report')

        sheet.merge_range(0, 0, 0, 25, "Cash Incentive Report", format0)
        sheet.merge_range(1, 0, 1, 25, "Period: {0} to {1}".format(start_date,end_date), format0)

        h_col = 0
        sheet.write(3, h_col, 'Sl No.', format1)
        h_col += 1
        sheet.write(3, h_col, 'Client Name', format1)
        h_col += 1
        sheet.write(3, h_col, 'Invoice No.', format1)
        h_col += 1
        sheet.write(3, h_col, 'Invoice Date', format1)
        h_col += 1
        sheet.write(3, h_col, 'Quantity', format1)
        h_col += 1
        # sheet.write(3, 2, 'Joining Date', format2)

        sheet.write(3, h_col, 'Invoice Amount (FC)', format1)
        h_col += 1
        sheet.write(3, h_col, 'Basis Fee', format1)
        h_col += 1
        sheet.write(3, h_col, 'SWIFT Amount (FC)', format1)
        h_col += 1

        sheet.write(3, h_col, 'Currency', format1)
        h_col += 1
        sheet.write(3, h_col, 'SWIFT/Nostro Date', format1)
        h_col += 1
        sheet.write(3, h_col, 'Current Date', format1)
        h_col += 1
        sheet.write(3, h_col, 'Application Deadline', format1)
        h_col += 1
        sheet.write(3, h_col, 'Remaining Days', format1)
        h_col += 1
        sheet.write(3, h_col, 'OD Sight Rate', format1)
        h_col += 1
        sheet.write(3, h_col, 'Incentive Amount (FC)', format1)
        h_col += 1
        sheet.write(3, h_col, 'Incentive Amount (BDT)', format1)
        h_col += 1
        sheet.write(3, h_col, 'Encashment Rate', format1)
        h_col += 1
        sheet.write(3, h_col, 'Equivalent taka', format1)
        h_col += 1
        sheet.write(3, h_col, 'Date Credited to Beneficirys A/C', format1)
        h_col += 1
        sheet.write(3, h_col, '(g) Reporting Statement/Schedule to BB with Month', format1)
        h_col += 1
        sheet.write(3, h_col, '(h) Reference of Online Reporting to BB', format1)
        h_col += 1
        sheet.write(3, h_col, 'Contract Price', format1)
        h_col += 1
        sheet.write(3, h_col, 'Ordering Customer Name & Address', format1)
        h_col += 1
        sheet.write(3, h_col, 'Ordering Institution Name & Address', format1)
        h_col += 1
        sheet.write(3, h_col, 'Contract No.', format1)
        h_col += 1
        sheet.write(3, h_col, 'Contract Date', format1)

        row = 4
        col = 0
        sl_no = 1
        search_domain = [('state', '!=', 'cancel'),
                         ('date', '>=', self.start_date),
                         ('date', '<=', self.end_date)]
        if self.reference:
            search_domain.append(('id', '=', self.reference.id))
        if self.partner_id:
            search_domain.append(('partner_id', '=',  self.partner_id.id))

        incentive_obj = self.env['cash.incentive.head'].search(search_domain, order='id asc')
        g_total_inv_amount = 0
        g_total_basis_fee_amt = 0
        g_total_swift_amt = 0
        g_total_od_sight_rate = 0
        g_total_incentive_amt_fc = 0
        g_total_incentive_amt_bdt = 0
        g_total_encashment_amt_bdt = 0

        for rec in incentive_obj:
            sheet.merge_range(row, 0, row, 25, 'Reference: '+rec.name, format8)
            row = row + 1
            row_count = row + len(rec.invoice_line_ids) - 1 if len(rec.invoice_line_ids) > 1 else row
            if len(rec.invoice_line_ids) > 1:
                sheet.merge_range(row, col, row_count, col, sl_no, format5)
                sheet.merge_range(row, col + 1, row_count, col + 1, rec.partner_id.name, format5)
            else:
                sheet.write(row, col, sl_no, format5)
                sheet.write(row, col+1, rec.partner_id.name, format5)

            total_inv_amount = 0
            total_basis_fee_amt = rec.basis_fee_amt
            total_swift_amt = 0
            total_od_sight_rate = 0
            total_incentive_amt_fc = 0
            total_incentive_amt_bdt = 0
            total_encashment_amt_bdt = 0

            invoice_groups = {}
            for x in rec.invoice_line_ids:
                if x.invoice_id.ref in invoice_groups:
                    invoice_groups[x.invoice_id.ref].append(x)
                else:
                    invoice_groups[x.invoice_id.ref] = [x]

            # Generate HTML for merged rows
            print(invoice_groups)

            for invoice_num, rows in invoice_groups.items():
                for i, line in enumerate(rows):
                    t_col = 2
                    # sheet.write(row, col, sl_no, format5)
                    if len(rows) > 1:
                        if i == 0:
                            sheet.merge_range(row, col + t_col, (row + len(rows)) -1 , col + t_col, line.invoice_id.ref, format5)
                    else:
                        sheet.write(row, col + t_col, line.invoice_id.ref, format5)
                    t_col += 1

                    if len(rows) > 1:
                        if i == 0:
                            if line.invoice_date:
                                sheet.merge_range(row, col + t_col, (row + len(rows)) - 1, col + t_col, datetime.datetime.strptime(str(line.invoice_date), '%Y-%m-%d').strftime('%d-%b-%y'), format5)
                            else:
                                sheet.merge_range(row, col + t_col, (row + len(rows)) - 1, col + t_col, '', format5)
                    else:
                        if line.invoice_date:
                            sheet.write(row, col + t_col, datetime.datetime.strptime(str(line.invoice_date), '%Y-%m-%d').strftime('%d-%b-%y'), format5)
                        else:
                            sheet.write(row, col + t_col, '', format5)
                    t_col += 1

                    if len(rows) > 1:
                        if i == 0:
                            sheet.merge_range(row, col + t_col, (row + len(rows)) -1 , col + t_col, line.invoice_qty_str, format5)
                    else:
                        sheet.write(row, col + t_col, line.invoice_qty_str, format5)
                    t_col += 1
                    # sheet.write(row, col + t_col, line.invoice_qty_str, format5)

                    if len(rows) > 1:
                        if i == 0:
                            sheet.merge_range(row, col + t_col, (row + len(rows)) -1 , col + t_col, line.invoice_amt, format9)
                            total_inv_amount += line.invoice_amt
                    else:
                        sheet.write(row, col + t_col, line.invoice_amt, format9)
                        total_inv_amount += line.invoice_amt
                    t_col += 1

                    # sheet.write(row, col + t_col, line.invoice_amt, format9)
                    # total_inv_amount += line.invoice_amt
                    # t_col += 1
                    sheet.write(row, col + t_col, '', format9)
                    t_col += 1
                    sheet.write(row, col + t_col, line.swift_amt, format9)
                    total_swift_amt += line.swift_amt
                    t_col += 1
                    sheet.write(row, col + t_col, line.currency_id.name, format5)
                    t_col += 1
                    if line.swift_message_id.date:
                        sheet.write(row, col + t_col,
                                    datetime.datetime.strptime(str(line.swift_message_id.date), '%Y-%m-%d').strftime(
                                        '%d-%b-%y'), format5)
                        t_col += 1
                    else:
                        sheet.write(row, col + t_col, '', format5)
                        t_col += 1
                    if rec.create_date:
                        sheet.write(row, col + t_col,
                                    datetime.datetime.strptime(rec.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                               '%Y-%m-%d %H:%M:%S').strftime('%d-%b-%y'), format5)
                        t_col += 1
                    else:
                        sheet.write(row, col + t_col, '', format5)
                        t_col += 1
                    if rec.application_deadline:
                        sheet.write(row, col + t_col,
                                    datetime.datetime.strptime(str(rec.application_deadline), '%Y-%m-%d').strftime(
                                        '%d-%b-%y'), format5)
                        t_col += 1
                    else:
                        sheet.write(row, col + t_col, '', format5)
                        t_col += 1
                    sheet.write(row, col + t_col, rec.remaining_days, format5)
                    t_col += 1
                    sheet.write(row, col + t_col, line.od_sight_rate, format9)
                    total_od_sight_rate += line.od_sight_rate
                    t_col += 1
                    sheet.write(row, col + t_col, line.incentive_amt_fc, format9)
                    total_incentive_amt_fc += line.incentive_amt_fc
                    t_col += 1
                    sheet.write(row, col + t_col, line.incentive_amt_bdt, format9)
                    total_incentive_amt_bdt += line.incentive_amt_bdt
                    t_col += 1
                    sheet.write(row, col + t_col, str(format(line.encashment_rate_bdt, '.4f')), format5)
                    t_col += 1
                    sheet.write(row, col + t_col, line.encashment_amt_bdt, format9)
                    total_encashment_amt_bdt += line.encashment_amt_bdt
                    t_col += 1
                    if rec.date_credited_beneficiaries:
                        sheet.write(row, col + t_col, datetime.datetime.strptime(str(rec.date_credited_beneficiaries),
                                                                                 '%Y-%m-%d').strftime('%d-%b-%y'),
                                    format5)
                        t_col += 1
                    else:
                        sheet.write(row, col + t_col, '', format5)
                        t_col += 1
                    sheet.write(row, col + t_col, rec.reporting_st_to_bb if rec.reporting_st_to_bb else '', format5)
                    t_col += 1
                    sheet.write(row, col + t_col, rec.ref_online_to_bb if rec.ref_online_to_bb else '', format5)
                    t_col += 1
                    sheet.write(row, col + t_col, rec.contract_price, format5)
                    t_col += 1
                    sheet.write(row, col + t_col, rec.customer_address, format5)
                    t_col += 1
                    sheet.write(row, col + t_col, rec.institution_address if rec.institution_address else '', format5)
                    t_col += 1
                    sheet.write(row, col + t_col, line.contract_number, format10)
                    t_col += 1
                    sheet.write(row, col + t_col, line.contract_date_str, format10)
                    t_col += 1
                    row = row + 1

            # for line in rec.invoice_line_ids:
            #     t_col = 2
            #     # sheet.write(row, col, sl_no, format5)
            #     sheet.write(row, col + t_col, line.invoice_id.ref, format5)
            #     t_col += 1
            #     if line.invoice_date:
            #         sheet.write(row, col + t_col, datetime.datetime.strptime(str(line.invoice_date), '%Y-%m-%d').strftime('%d-%b-%y'), format5)
            #         t_col += 1
            #     else:
            #         sheet.write(row, col + t_col, '', format5)
            #         t_col += 1
            #     sheet.write(row, col + t_col, line.invoice_qty_str, format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.invoice_amt, format9)
            #     total_inv_amount += line.invoice_amt
            #     t_col += 1
            #     sheet.write(row, col + t_col, '', format9)
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.swift_amt, format9)
            #     total_swift_amt += line.swift_amt
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.currency_id.name, format5)
            #     t_col += 1
            #     if line.swift_message_id.date:
            #         sheet.write(row, col + t_col, datetime.datetime.strptime(str(line.swift_message_id.date), '%Y-%m-%d').strftime('%d-%b-%y'), format5)
            #         t_col += 1
            #     else:
            #         sheet.write(row, col + t_col, '', format5)
            #         t_col += 1
            #     if rec.create_date:
            #         sheet.write(row, col + t_col, datetime.datetime.strptime(rec.create_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').strftime('%d-%b-%y'), format5)
            #         t_col += 1
            #     else:
            #         sheet.write(row, col + t_col, '', format5)
            #         t_col += 1
            #     if rec.application_deadline:
            #         sheet.write(row, col + t_col, datetime.datetime.strptime(str(rec.application_deadline), '%Y-%m-%d').strftime('%d-%b-%y'), format5)
            #         t_col += 1
            #     else:
            #         sheet.write(row, col + t_col, '', format5)
            #         t_col += 1
            #     sheet.write(row, col + t_col, rec.remaining_days, format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.od_sight_rate, format9)
            #     total_od_sight_rate += line.od_sight_rate
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.incentive_amt_fc, format9)
            #     total_incentive_amt_fc += line.incentive_amt_fc
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.incentive_amt_bdt, format9)
            #     total_incentive_amt_bdt += line.incentive_amt_bdt
            #     t_col += 1
            #     sheet.write(row, col + t_col, str(format(line.encashment_rate_bdt, '.4f')) , format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.encashment_amt_bdt, format9)
            #     total_encashment_amt_bdt += line.encashment_amt_bdt
            #     t_col += 1
            #     if rec.date_credited_beneficiaries:
            #         sheet.write(row, col + t_col, datetime.datetime.strptime(str(rec.date_credited_beneficiaries), '%Y-%m-%d').strftime('%d-%b-%y'), format5)
            #         t_col += 1
            #     else:
            #         sheet.write(row, col + t_col, '', format5)
            #         t_col += 1
            #     sheet.write(row, col + t_col, rec.reporting_st_to_bb if rec.reporting_st_to_bb else '', format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, rec.ref_online_to_bb if rec.ref_online_to_bb else '', format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, rec.contract_price, format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, rec.customer_address, format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, rec.institution_address if rec.institution_address else '', format5)
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.contract_number, format10)
            #     t_col += 1
            #     sheet.write(row, col + t_col, line.contract_date_str, format10)
            #     t_col += 1
            #     row = row + 1

            sheet.write(row, 3, 'Total', format6)
            sheet.write(row, 5, total_inv_amount, format6)
            g_total_inv_amount += total_inv_amount
            sheet.write(row, 6, total_basis_fee_amt, format6)
            g_total_basis_fee_amt += total_basis_fee_amt
            sheet.write(row, 7, total_swift_amt, format6)
            g_total_swift_amt += total_swift_amt
            sheet.write(row, 13, total_od_sight_rate, format6)
            g_total_od_sight_rate += total_od_sight_rate
            sheet.write(row, 14, total_incentive_amt_fc, format6)
            g_total_incentive_amt_fc += total_incentive_amt_fc
            sheet.write(row, 15, total_incentive_amt_bdt, format6)
            g_total_incentive_amt_bdt += total_incentive_amt_bdt
            sheet.write(row, 17, total_encashment_amt_bdt, format6)
            g_total_encashment_amt_bdt += total_encashment_amt_bdt
            row = row + 1
            sl_no = sl_no + 1

        sheet.write(row, 0, '', format6)
        sheet.write(row, 1, '', format6)
        sheet.write(row, 2, '', format6)
        sheet.write(row, 3, 'Grand Total', format6)
        sheet.write(row, 4, '', format6)
        sheet.write(row, 5, g_total_inv_amount, format6)
        sheet.write(row, 6, g_total_basis_fee_amt, format6)
        sheet.write(row, 7, g_total_swift_amt, format6)
        sheet.write(row, 8, '', format6)
        sheet.write(row, 9, '', format6)
        sheet.write(row, 10, '', format6)
        sheet.write(row, 11, '', format6)
        sheet.write(row, 12, '', format6)
        sheet.write(row, 13, g_total_od_sight_rate, format6)
        sheet.write(row, 14, g_total_incentive_amt_fc, format6)
        sheet.write(row, 15, g_total_incentive_amt_bdt, format6)
        sheet.write(row, 16, '', format6)
        sheet.write(row, 17, g_total_encashment_amt_bdt, format6)
        sheet.write(row, 18, '', format6)
        sheet.write(row, 19, '', format6)
        sheet.write(row, 20, '', format6)
        sheet.write(row, 21, '', format6)
        sheet.write(row, 22, '', format6)
        sheet.write(row, 23, '', format6)
        sheet.write(row, 24, '', format6)
        sheet.write(row, 25, '', format6)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Cash Incentive Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=cash.incentive.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def cash_incentive_report_sql(self, start_date, end_date):
        self.env.cr.execute("""select polc.*, rp.name, rp.street, rp.street2, rp.city,bb.name branch,ba.name bank,
                              st.name as state, rc.name as country, po.name as po_name
                              from purchase_order_lc polc 
                              left join res_partner rp on rp.id = polc.vendor_id 
                              left join res_country_state st on st.id = rp.state_id 
                              left join res_country rc on rc.id = rp.country_id 
                              left join purchase_order po on po.id = polc.po_id 
                              left join cheque_book_bank_branch bb on bb.id = polc.bank_branch_id 
                              left join cheque_book_bank ba on ba.id = polc.bank_id 
                              where DATE(polc.create_date) between '{0}' and '{1}' and polc.state != 'cancel'
                               """.format(start_date, end_date))
        lc_list = self.env.cr.dictfetchall()

        data = {
            'model': 'cash.incentive.wizard',
            'form': self.read()[0],
            'csr': lc_list,
            'start_date':  datetime.datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%y'),
            'end_date': datetime.datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%y'),
        }
        return data