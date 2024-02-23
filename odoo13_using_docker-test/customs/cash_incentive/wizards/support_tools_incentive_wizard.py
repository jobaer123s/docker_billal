from odoo import exceptions, fields, models, _, api

from odoo.addons.helper import validator
from odoo.exceptions import UserError, ValidationError


class SupportToolsIncentiveWizard(models.TransientModel):
    _name = "support.tools.incentive.wizard"

    type = fields.Selection([('1', 'Only Swift Status Draft'),
                            ('2', 'Swift Status Draft and Invoice New'),
                             ('3', 'Cash Incentive File Delete'),
                             ('4', 'Unlock Invoice or Invoice New (Warning: check if multiple swift encashment)'),
                            ], string='Type')

    swift_no = fields.Char("Swift (ERP Code)", help="Like 'SF00001'")
    invoice_no = fields.Char("Invoice Ref.", help="Like '7452'")
    file_no = fields.Char("Cash Incentive File (Reference)", help="Like 'BS-23-CIF/23/MBL123'")

    def action_update(self):
        if self.type == '1':
            if not self.swift_no:
                raise UserError(message=_("Required Swift (ERP Code)!"))

            else:
                swift_obj = self.env['swift.message'].sudo().search([('code', '=', self.swift_no)], limit=1)
                if not swift_obj:
                    raise UserError(message=_("Invalid Swift (ERP Code)!"))
                else:
                    self.env.cr.execute("""update swift_message set state='draft' where code='%s'""" %(self.swift_no))

        elif self.type == '2':
            if not self.swift_no:
                raise UserError(message=_("Required Swift (ERP Code)!"))
            else:
                swift_obj = self.env['swift.message'].sudo().search([('code', '=', self.swift_no)], limit=1)
                if not swift_obj:
                    raise UserError(message=_("Invalid Swift (ERP Code)!"))
                else:
                    swift_id = swift_obj.id
                    inv_ids = self.env['cash.incentive.invoice'].sudo().search([('swift_message_id', '=', swift_id)])
                    inv_refs = ''
                    for rec in inv_ids:
                        if rec.invoice_id.ref:
                            if inv_refs == '':
                                inv_refs = "'" +str(rec.invoice_id.ref) + "'"
                            else:
                                inv_refs += ", '" +str(rec.invoice_id.ref) + "'"

                    self.env.cr.execute("""update swift_message set state='draft' where code='%s'""" %(self.swift_no))
                    if inv_refs:
                        self.env.cr.execute("""update account_move set payment_state='not_paid', is_done_inv_amount=false, invoice_payment_amount_fc=0, swift_remaining_amount=0 where ref in (%s)""" % (inv_refs))

                    #----------------
                    # account_move_obj = self.env['account.move'].sudo().search([('swift_id', '=', swift_id)])
                    # for row in account_move_obj:
                    #     row.sudo().button_draft()
                        #row.unlink()

        elif self.type == '3':
            if not self.file_no:
                raise UserError(message=_("Required Cash Incentive File (Reference)!"))
            else:
                self.env.cr.execute("""delete from cash_incentive_head where name = '%s'""" %(self.file_no))

        elif self.type == '4':
            invoice_no = str(self.invoice_no).strip()
            if not invoice_no:
                raise UserError(message=_("Required Invoice Ref.!"))
            else:
                inv_obj = self.env['account.move'].sudo().search([('ref', '=', invoice_no)], limit=1)
                if not inv_obj:
                    raise UserError(message=_("Invalid Invoice Ref.!"))
                else:
                    self.env.cr.execute("""update account_move set payment_state='not_paid', is_done_inv_amount=false,invoice_payment_amount_fc=0,swift_remaining_amount=0 where ref='%s'""" %(invoice_no))

        return {'type': 'ir.actions.client',
                'tag': 'reload'
                }
