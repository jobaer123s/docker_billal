from odoo import exceptions, fields, models, _, api
from odoo.exceptions import UserError
from odoo.addons.helper import validator
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Many2one
import datetime
import base64, io, csv


class UploadInvoiceWizard(models.TransientModel):
    _name = "upload.invoice.wizard"

    inv_file = fields.Binary(string='Invoice File', attachment=True)
    inv_file_name = fields.Char("File Name")
    upload_des = fields.Text(string="Description")

    def csv_file_upload(self):
        csv_data = base64.b64decode(self.inv_file)
        data_file = io.StringIO(csv_data.decode("utf-8"))
        data_file.seek(0)
        csv_input = csv.DictReader(data_file)
        # print(csv_input)

        result = {}
        for d in csv_input:
            print(d['Rate'])
            if float(d['Rate']) > 0.0:
                client_name = ''
                invoice_name = ''
                client_substring = 'Client Name'
                inv_substring = 'Invoice #'
                for key in d:
                    if client_substring in key:
                        client_name = d[key]
                    if inv_substring in key:
                        invoice_name = d[key]
                # rint(d)
                if not inv_substring:
                    raise ValidationError(_('Please Upload a Valid CSV File.'))
                id = invoice_name
                partner_id = client_name
                date_issued = d['Date Issued']
                currency = d['Currency']
                if id in result:
                    product_dict = [{"item_id": d['Item Name'],
                                     "description": d['Item Description'],
                                     "rate": d['Rate'],
                                     "qty": d['Quantity'],
                                     "discount": d['Discount Percentage']}]
                    result[id]['item_ids'].append(product_dict)
                else:
                    result[id] = {"inv_ref": id, "partner_id": partner_id, "date_issued": date_issued, "currency": currency,
                                  "item_ids": []}
                    result[id]['item_ids'].append([{"item_id": d['Item Name'],
                                                    "description": d['Item Description'],
                                                    "rate": d['Rate'],
                                                    "qty": d['Quantity'],
                                                    "discount": d['Discount Percentage'],
                                                    }])

        result = [r for r in result.values()]
        duplicate_count = 0
        loop_count = 0
        article_count = 0
        error_str = ''
        partner_not_found_lis = []
        for data in result:
            loop_count += 1
            invoice_line = []
            partner_obj = self.env['res.partner'].search([('name', '=ilike', data['partner_id'])], limit=1)
            inv_obj = self.env['account.move'].search([('ref', '=', data['inv_ref'])], limit=1)
            currency_obj = self.env['res.currency'].search([('name', '=ilike', data['currency'])], limit=1)
            if inv_obj:
                duplicate_count += 1
                continue

            if not partner_obj:
                if data['partner_id'] not in partner_not_found_lis:
                    partner_not_found_lis.append(data['partner_id'])
                    error_str += "Error: Customer is not available with this name %s" % (data['partner_id']) + '\n'
                continue
                # raise ValidationError(_('Customer is not available with this name %s.') % data['partner_id'])

            if currency_obj.name != 'BDT':
                currency_id = currency_obj.id
            else:
                currency_id = None

            if '/' in data['date_issued']:
                try:
                    inv_date = datetime.datetime.strptime(str(data['date_issued']), '%d/%m/%Y').strftime('%Y-%m-%d')
                except:
                    try:
                        inv_date = datetime.datetime.strptime(str(data['date_issued']), '%d/%m/%y').strftime('%Y-%m-%d')
                    except:
                        try:
                            inv_date = datetime.datetime.strptime(str(data['date_issued']), '%m/%d/%y').strftime('%Y-%m-%d')
                        except:
                            inv_date = datetime.datetime.strptime(str(data['date_issued']), '%m/%d/%Y').strftime('%Y-%m-%d')

            else:
                try:
                    inv_date = datetime.datetime.strptime(str(data['date_issued']), '%d-%m-%Y').strftime('%Y-%m-%d')
                except:
                    try:
                        inv_date = datetime.datetime.strptime(str(data['date_issued']), '%d-%m-%y').strftime('%Y-%m-%d')
                    except:
                        try:
                            inv_date = datetime.datetime.strptime(str(data['date_issued']), '%m-%d-%y').strftime('%Y-%m-%d')
                        except:
                            inv_date = datetime.datetime.strptime(str(data['date_issued']), '%m-%d-%Y').strftime('%Y-%m-%d')

            usd_rate = 0
            currency_rate_obj = self.env['currency.conversion.rate'].search(
                [('date', '<=', inv_date), ('currency_id', '=', currency_obj.id),
                 ('type', '=', '01')],
                order='date DESC', limit=1)
            if currency_rate_obj:
                usd_rate = currency_rate_obj.rate

            for rec in data['item_ids']:
                product_obj = self.env['product.product'].search([('name', '=ilike', rec[0]['item_id'])], limit=1)
                if not product_obj:
                    product_obj = self.env['product.product'].search([('is_default_invoice_product', '=', True)], limit=1)
                    if not product_obj:
                        error_str += "Error: A Default Product is Mandatory.s" + '\n'
                        continue
                        # raise ValidationError(_('A Default Product is Mandatory.'))

                moveLineData = {
                    'name': rec[0]['item_id'] + ' - ' + str(rec[0]['description']),
                    'parent_state': 'draft',
                    'partner_id': partner_obj.id,
                    'product_id': product_obj.id,
                    'product_uom_id': product_obj.uom_id.id,
                    'quantity': rec[0]['qty'],
                    'usd_price': rec[0]['rate'] if currency_id != None else 0,
                    'quantity_type': '0' if float(rec[0]['rate']) <= 30 else '1',
                    'price_unit': rec[0]['rate'] if currency_id == None else float(rec[0]['rate']) * usd_rate,
                    # 'price_unit': float(rec[0]['rate']) * usd_rate,
                    'discount': rec[0]['discount'],
                }
                invoice_line.append((0, 0, moveLineData))

            move_vals = {
                'state': 'draft',
                'partner_id': partner_obj.id,
                'ref': data['inv_ref'],
                'move_type': 'out_invoice',
                'date': inv_date,
                'invoice_date': inv_date,
                'foreign_currency_type': currency_id,
                'usd_rate': usd_rate,
                'name': '/',
                'invoice_line_ids': invoice_line
            }
            inv_data = self.env['account.move'].create(move_vals)
            article_count += 1
            # inv_data._onchange_usd_rate()
            # inv_data._onchange_partner_id()
            if inv_data.terms_condition_id:
                inv_data.terms_condtion_details = inv_data.terms_condition_id.description
            date_before = inv_data.date

            # inv_data.post()
            inv_data.date = date_before
        if not error_str:
            return {'type': 'ir.actions.client', 'tag': 'reload', }
        upload_des = 'Total Rows: ' + str(loop_count) + '\nAlready Exists Invoice: ' + str(duplicate_count) + '\nImport Rows: ' + str(article_count) + '\n ========= Error List ==========:\n' + str(error_str)
        self.upload_des = upload_des
        return {
            'name': _('Upload Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'upload.invoice.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        #

    def action_sample_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/cash_incentive/static/src/sample_inv_upload_file.csv',
            'target': 'self',
        }
