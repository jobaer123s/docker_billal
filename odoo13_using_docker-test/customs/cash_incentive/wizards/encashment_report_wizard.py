from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from calendar import monthrange

from itertools import groupby
from datetime import datetime,date
from dateutil.relativedelta import relativedelta

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO

import pandas as pd


class EncashementReportWizard(models.TransientModel):
    _name = "encashment.report.wizard"
    _description = "Encashment Wizard"

    date_from = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    partner_id = fields.Many2one('res.partner', string='Customer')
    file_data = fields.Binary('Report File')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError(_("'Date From' must be earlier than 'Date To'."))


    def invoice_wise_encashment_report_excel(self):
        partner_id = self.partner_id
        search_domain = [('swift_msg_state', '=', 'pay'),
                         ('encashment_date', '>=', self.date_from),
                         ('encashment_date', '<=', self.date_to)]
        if self.partner_id:
            search_domain.append(('partner_id', '=', self.partner_id.id))
        incentive_obj = self.env['cash.incentive.invoice'].sudo().search(search_domain, order='encashment_date asc, invoice_ref asc')

        #--------------------------------------------
        file_name = "Encashment report- %s.xlsx" % (partner_id.name or 'ALL')
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

        # main header formatting
        format0 = workbook.add_format({'font_size': 12, 'align': 'vcenter', 'bold': True})
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
        format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format6.set_align('right')
        format6.set_border()

        # grand total formatting
        format7 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
        format7.set_border()
        format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
        format8.set_border()
        format9 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format9.set_border()

        sheet_all = workbook.add_worksheet('ALL')
        sheet_all.merge_range(0, 1, 0, 6, "Encashment report", format0)
        sheet_all.merge_range(1, 1, 1, 6, "Customer:%s" % (partner_id.name or 'ALL'), format0)
        sheet_all.merge_range(2, 1, 2, 6, "From Date:%s" % (datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%d-%b-%Y')), format0)
        sheet_all.merge_range(3, 1, 3, 6, "To Date:%s" % (datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%d-%b-%Y')), format0)

        #------------------------------------------- ALL
        row = 5
        col = 0
        sl_no = 1
        summary_list = []
        for rec in incentive_obj:
            nw_dt = datetime.strptime(str(rec.encashment_date), '%Y-%m-%d').strftime('%d-%m-%Y')

            #---------------
            total_bdt_dr = 0
            total_bdt_cr = 0

            #--------------- Invoice Title
            col = col + 1
            sheet_all.write(row, col, 'Invoice', format2)
            col = col + 1
            sheet_all.write(row, col, str(rec.invoice_id.ref or '-'), format2)
            col = col + 1
            sheet_all.write(row, col, 'BDT', format2)
            col = col + 1
            sheet_all.write(row, col, 'BDT', format2)
            col = col + 1
            sheet_all.write(row, col, str(rec.currency_id.name or '-'), format2)
            col = col + 1
            sheet_all.write(row, col, 'Exchange rate', format2)
            row += 1
            col = 0
            #-------------- Encashment
            col = col + 1
            sheet_all.write(row, col, 'Debit', format5)
            col = col + 1
            sheet_all.write(row, col, rec.encashment_acc_id.name, format5)
            col = col + 1
            sheet_all.write(row, col, rec.encashment_amt_bdt, format5)
            total_bdt_dr += rec.encashment_amt_bdt

            col = col + 1
            sheet_all.write(row, col, 0, format5)
            col = col + 1
            sheet_all.write(row, col, rec.encashment_amt_fc, format5)
            col = col + 1
            sheet_all.write(row, col, rec.encashment_rate_bdt, format5)
            row += 1
            col = 0
            #------------------ ERQ
            col = col + 1
            sheet_all.write(row, col, 'Debit', format5)
            col = col + 1
            sheet_all.write(row, col, rec.erq_acc_id.name, format5)
            col = col + 1
            sheet_all.write(row, col, rec.erq_amt_bdt, format5)
            total_bdt_dr += rec.erq_amt_bdt

            col = col + 1
            sheet_all.write(row, col, 0, format5)
            col = col + 1
            sheet_all.write(row, col, rec.erq_amt_fc, format5)
            col = col + 1
            sheet_all.write(row, col, rec.erq_rate_bdt, format5)
            row += 1
            col = 0
            # ------------------Bank Charge
            col = col + 1
            sheet_all.write(row, col, 'Debit', format5)
            col = col + 1
            sheet_all.write(row, col, rec.bank_charge_acc_id.name, format5)
            col = col + 1
            sheet_all.write(row, col, rec.swift_charge_bdt, format5)
            total_bdt_dr += rec.swift_charge_bdt

            col = col + 1
            sheet_all.write(row, col, 0, format5)
            col = col + 1
            sheet_all.write(row, col, rec.swift_charge_fc, format5)
            col = col + 1
            sheet_all.write(row, col, rec.usd_rate, format5)
            row += 1
            col = 0
            # ------------------Receivable
            col = col + 1
            sheet_all.write(row, col, 'Credit', format5)
            col = col + 1
            sheet_all.write(row, col, rec.partner_cr_acc_id.name, format5)
            col = col + 1
            sheet_all.write(row, col, 0, format5)
            col = col + 1
            sheet_all.write(row, col, rec.total_swift_amt_bdt, format5)
            total_bdt_cr += rec.total_swift_amt_bdt

            col = col + 1
            sheet_all.write(row, col, rec.total_swift_amt, format5)
            col = col + 1
            sheet_all.write(row, col, rec.usd_rate, format5)
            row += 1
            col = 0
            # ------------------Gain/Loss
            col = col + 1
            sheet_all.write(row, col, 'Credit', format5)
            col = col + 1
            sheet_all.write(row, col, rec.fc_gain_loss_acc_id.name, format5)
            col = col + 1
            sheet_all.write(row, col, '', format5)
            col = col + 1
            sheet_all.write(row, col, rec.difference_amnt_bdt, format5)
            total_bdt_cr += rec.difference_amnt_bdt

            col = col + 1
            sheet_all.write(row, col, '', format5)
            col = col + 1
            sheet_all.write(row, col, '', format5)
            row += 1
            col = 0
            # ------------------Incoie Total
            col = col + 1
            sheet_all.write(row, col, '', format2)
            col = col + 1
            sheet_all.write(row, col, '', format2)
            col = col + 1
            sheet_all.write(row, col, total_bdt_dr, format2)
            col = col + 1
            sheet_all.write(row, col, total_bdt_cr, format2)
            col = col + 1
            sheet_all.write(row, col, '', format2)
            col = col + 1
            sheet_all.write(row, col, '', format2)
            row += 1
            col = 0
            #------------
            row = row + 1


            #---------summary
            summary_list.append({
                'b_acc': rec.encashment_acc_id.name,
                'b_local_dr': rec.encashment_amt_bdt,
                'b_local_cr': 0
            })
            summary_list.append({
                'b_acc': rec.erq_acc_id.name,
                'b_local_dr': rec.erq_amt_bdt,
                'b_local_cr': 0
            })
            summary_list.append({
                'b_acc': rec.bank_charge_acc_id.name,
                'b_local_dr': rec.swift_charge_bdt,
                'b_local_cr': 0
            })
            summary_list.append({
                'b_acc': rec.partner_cr_acc_id.name,
                'b_local_dr': 0,
                'b_local_cr': rec.total_swift_amt_bdt
            })
            summary_list.append({
                'b_acc': rec.fc_gain_loss_acc_id.name,
                'b_local_dr': 0,
                'b_local_cr': rec.difference_amnt_bdt
            })
            # ------------------ End all

        #----------------- Summary
        df = pd.DataFrame(summary_list)
        dg = df.groupby('b_acc', as_index=False).sum()
        summary_data_list = dg.to_dict('records')
        # ------------------Incoie Total
        row += 2
        col = col + 2
        sheet_all.write(row, col, 'SUMMARY', format2)
        col = col + 1
        sheet_all.write(row, col, 'DR', format2)
        col = col + 1
        sheet_all.write(row, col, 'CR', format2)
        row += 1
        col = 0
        # ------------
        sum_dr=0
        sum_cr=0
        for i in range(len(summary_data_list)):
            sum_dict = summary_data_list[i]
            b_acc = sum_dict['b_acc']
            b_local_dr = sum_dict['b_local_dr']
            b_local_cr = sum_dict['b_local_cr']
            sum_dr += b_local_dr
            sum_cr += b_local_cr
            # ------------------Total
            col = col + 2
            sheet_all.write(row, col, b_acc, format8)
            col = col + 1
            sheet_all.write(row, col, b_local_dr, format2)
            col = col + 1
            sheet_all.write(row, col, b_local_cr, format2)
            row += 1
            col = 0
            # ------------
        col = col + 2
        sheet_all.write(row, col, '', format2)
        col = col + 1
        sheet_all.write(row, col, sum_dr, format2)
        col = col + 1
        sheet_all.write(row, col, sum_cr, format2)
        row += 1
        col = 0

        # ------------------------------- Datewise
        summary_list = []
        inv_list = []
        sl_no = 1
        prev_dt = ''
        for rec in incentive_obj:
            nw_dt = datetime.strptime(str(rec.encashment_date), '%Y-%m-%d').strftime('%d-%m-%Y')
            nw_dt_chk = str(nw_dt).replace('-', '')
            if nw_dt_chk != prev_dt:
                #-----------------------------------
                if prev_dt != '':
                # ----------------- Summary
                    df = pd.DataFrame(summary_list)
                    dg = df.groupby('b_acc', as_index=False).sum()
                    summary_data_list = dg.to_dict('records')
                    # ------------------Incoie Total
                    row += 2
                    col = col + 2
                    sheet.write(row, col, 'SUMMARY', format2)
                    col = col + 1
                    sheet.write(row, col, 'DR', format2)
                    col = col + 1
                    sheet.write(row, col, 'CR', format2)
                    row += 1
                    col = 0
                    # ------------
                    sum_dr = 0
                    sum_cr = 0
                    for i in range(len(summary_data_list)):
                        sum_dict = summary_data_list[i]
                        b_acc = sum_dict['b_acc']
                        b_local_dr = sum_dict['b_local_dr']
                        b_local_cr = sum_dict['b_local_cr']
                        sum_dr += b_local_dr
                        sum_cr += b_local_cr
                        # ------------------Total
                        col = col + 2
                        sheet.write(row, col, b_acc, format8)
                        col = col + 1
                        sheet.write(row, col, b_local_dr, format2)
                        col = col + 1
                        sheet.write(row, col, b_local_cr, format2)
                        row += 1
                        col = 0
                        # ------------
                    col = col + 2
                    sheet.write(row, col, '', format2)
                    col = col + 1
                    sheet.write(row, col, sum_dr, format2)
                    col = col + 1
                    sheet.write(row, col, sum_cr, format2)
                    row += 1
                    col = 0
                    summary_list = []



                #-------------------------------------------------------
                prev_dt = nw_dt_chk
                # ---
                sheet = workbook.add_worksheet(nw_dt)
                sheet.merge_range(0, 1, 0, 6, "Encashment report", format0)
                sheet.merge_range(1, 1, 1, 6, "Customer:%s" % (partner_id.name or 'ALL'), format0)
                sheet.merge_range(2, 1, 2, 6, "From Date:%s" % (
                    datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%d-%b-%Y')), format0)
                sheet.merge_range(3, 1, 3, 6, "To Date:%s" % (
                    datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%d-%b-%Y')),
                                  format0)
                row = 5
                col = 0

            # ---------------
            total_bdt_dr = 0
            total_bdt_cr = 0

            # --------------- Invoice Title
            col = col + 1
            sheet.write(row, col, 'Invoice', format2)
            col = col + 1
            sheet.write(row, col, str(rec.invoice_id.ref or '-'), format2)
            col = col + 1
            sheet.write(row, col, 'BDT', format2)
            col = col + 1
            sheet.write(row, col, 'BDT', format2)
            col = col + 1
            sheet.write(row, col, str(rec.currency_id.name or '-'), format2)
            col = col + 1
            sheet.write(row, col, 'Exchange rate', format2)
            row += 1
            col = 0
            # -------------- Encashment
            line_list = []
            # line_list.append({'b_inv_dr_cr': 'Debit',
            #                   'b_acc': rec.encashment_acc_id.name,
            #                   'b_local_dr': rec.encashment_amt_bdt,
            #                   'b_local_cr': '',
            #                   'b_foreign_fc': rec.encashment_amt_fc,
            #                   'b_exchange_rate': rec.encashment_rate_bdt
            #                   })
            col = col + 1
            sheet.write(row, col, 'Debit', format5)
            col = col + 1
            sheet.write(row, col, rec.encashment_acc_id.name, format5)
            col = col + 1
            sheet.write(row, col, rec.encashment_amt_bdt, format5)
            total_bdt_dr += rec.encashment_amt_bdt

            col = col + 1
            sheet.write(row, col, 0, format5)
            col = col + 1
            sheet.write(row, col, rec.encashment_amt_fc, format5)
            col = col + 1
            sheet.write(row, col, rec.encashment_rate_bdt, format5)
            row += 1
            col = 0
            # ------------------ ERQ
            # line_list.append({'b_inv_dr_cr': 'Debit',
            #                   'b_acc': rec.erq_acc_id.name,
            #                   'b_local_dr': rec.erq_amt_bdt,
            #                   'b_local_cr': '',
            #                   'b_foreign_fc': rec.erq_amt_fc,
            #                   'b_exchange_rate': rec.erq_rate_bdt
            #                   })
            col = col + 1
            sheet.write(row, col, 'Debit', format5)
            col = col + 1
            sheet.write(row, col, rec.erq_acc_id.name, format5)
            col = col + 1
            sheet.write(row, col, rec.erq_amt_bdt, format5)
            total_bdt_dr += rec.erq_amt_bdt

            col = col + 1
            sheet.write(row, col, 0, format5)
            col = col + 1
            sheet.write(row, col, rec.erq_amt_fc, format5)
            col = col + 1
            sheet.write(row, col, rec.erq_rate_bdt, format5)
            row += 1
            col = 0
            # ------------------Bank Charge
            # line_list.append({'b_inv_dr_cr': 'Debit',
            #                   'b_acc': rec.bank_charge_acc_id.name,
            #                   'b_local_dr': rec.swift_charge_bdt,
            #                   'b_local_cr': '',
            #                   'b_foreign_fc': rec.swift_charge_fc,
            #                   'b_exchange_rate': rec.usd_rate
            #                   })
            col = col + 1
            sheet.write(row, col, 'Debit', format5)
            col = col + 1
            sheet.write(row, col, rec.bank_charge_acc_id.name, format5)
            col = col + 1
            sheet.write(row, col, rec.swift_charge_bdt, format5)
            total_bdt_dr += rec.swift_charge_bdt

            col = col + 1
            sheet.write(row, col, 0, format5)
            col = col + 1
            sheet.write(row, col, rec.swift_charge_fc, format5)
            col = col + 1
            sheet.write(row, col, rec.usd_rate, format5)
            row += 1
            col = 0
            # ------------------Receivable
            # line_list.append({'b_inv_dr_cr': 'Credit',
            #                   'b_acc': rec.partner_cr_acc_id.name,
            #                   'b_local_dr': '',
            #                   'b_local_cr': rec.total_swift_amt_bdt,
            #                   'b_foreign_fc': rec.total_swift_amt,
            #                   'b_exchange_rate': rec.usd_rate
            #                   })
            col = col + 1
            sheet.write(row, col, 'Credit', format5)
            col = col + 1
            sheet.write(row, col, rec.partner_cr_acc_id.name, format5)
            col = col + 1
            sheet.write(row, col, 0, format5)
            col = col + 1
            sheet.write(row, col, rec.total_swift_amt_bdt, format5)
            total_bdt_cr += rec.total_swift_amt_bdt

            col = col + 1
            sheet.write(row, col, rec.total_swift_amt, format5)
            col = col + 1
            sheet.write(row, col, rec.usd_rate, format5)
            row += 1
            col = 0
            # ------------------Gain/Loss
            # line_list.append({'b_inv_dr_cr': 'Credit',
            #                   'b_acc': rec.fc_gain_loss_acc_id.name,
            #                   'b_local_dr': '',
            #                   'b_local_cr': rec.difference_amnt_bdt,
            #                   'b_foreign_fc': '',
            #                   'b_exchange_rate': ''
            #                   })
            # dict_data['lines']= line_list
            # inv_list.append(dict_data)
            col = col + 1
            sheet.write(row, col, 'Credit', format5)
            col = col + 1
            sheet.write(row, col, rec.fc_gain_loss_acc_id.name, format5)
            col = col + 1
            sheet.write(row, col, '', format5)
            col = col + 1
            sheet.write(row, col, rec.difference_amnt_bdt, format5)
            total_bdt_cr += rec.difference_amnt_bdt

            col = col + 1
            sheet.write(row, col, '', format5)
            col = col + 1
            sheet.write(row, col, '', format5)
            row += 1
            col = 0
            # ------------------Incoie Total
            col = col + 1
            sheet.write(row, col, '', format2)
            col = col + 1
            sheet.write(row, col, '', format2)
            col = col + 1
            sheet.write(row, col, total_bdt_dr, format2)
            col = col + 1
            sheet.write(row, col, total_bdt_cr, format2)
            col = col + 1
            sheet.write(row, col, '', format2)
            col = col + 1
            sheet.write(row, col, '', format2)
            row += 1
            col = 0
            # ------------
            row = row + 1
            # ------------------
            # ---------summary
            summary_list.append({
                'b_acc': rec.encashment_acc_id.name,
                'b_local_dr': rec.encashment_amt_bdt,
                'b_local_cr': 0
            })
            summary_list.append({
                'b_acc': rec.erq_acc_id.name,
                'b_local_dr': rec.erq_amt_bdt,
                'b_local_cr': 0
            })
            summary_list.append({
                'b_acc': rec.bank_charge_acc_id.name,
                'b_local_dr': rec.swift_charge_bdt,
                'b_local_cr': 0
            })
            summary_list.append({
                'b_acc': rec.partner_cr_acc_id.name,
                'b_local_dr': 0,
                'b_local_cr': rec.total_swift_amt_bdt
            })
            summary_list.append({
                'b_acc': rec.fc_gain_loss_acc_id.name,
                'b_local_dr': 0,
                'b_local_cr': rec.difference_amnt_bdt
            })


        #-------------
        if len(summary_list) > 0:
            # ----------------- Summary
            df = pd.DataFrame(summary_list)
            dg = df.groupby('b_acc', as_index=False).sum()
            summary_data_list = dg.to_dict('records')
            # ------------------Incoie Total
            row += 2
            col = col + 2
            sheet.write(row, col, 'SUMMARY', format2)
            col = col + 1
            sheet.write(row, col, 'DR', format2)
            col = col + 1
            sheet.write(row, col, 'CR', format2)
            row += 1
            col = 0
            # ------------
            sum_dr = 0
            sum_cr = 0
            for i in range(len(summary_data_list)):
                sum_dict = summary_data_list[i]
                b_acc = sum_dict['b_acc']
                b_local_dr = sum_dict['b_local_dr']
                b_local_cr = sum_dict['b_local_cr']
                sum_dr += b_local_dr
                sum_cr += b_local_cr
                # ------------------Total
                col = col + 2
                sheet.write(row, col, b_acc, format8)
                col = col + 1
                sheet.write(row, col, b_local_dr, format2)
                col = col + 1
                sheet.write(row, col, b_local_cr, format2)
                row += 1
                col = 0
                # ------------
            col = col + 2
            sheet.write(row, col, '', format2)
            col = col + 1
            sheet.write(row, col, sum_dr, format2)
            col = col + 1
            sheet.write(row, col, sum_cr, format2)
            row += 1
            col = 0

        #----------------------
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()
        return {
            'name': 'Encashment Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=encashment.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }