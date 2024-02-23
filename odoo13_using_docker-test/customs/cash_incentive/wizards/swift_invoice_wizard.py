from odoo import exceptions,fields, models, _, api
from odoo.exceptions import UserError
from odoo.addons.helper import validator
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Many2one


class JournalWizard(models.TransientModel):
    _name = "journal.wizard"

    swift_id = fields.Many2one('swift.message', string='Swift')
    partner_id = fields.Many2one('res.partner', 'Customer')
    bank_id = fields.Many2one('res.bank', string='SWIFT Bank', domain="[('is_cash_incentive_bank', '=', True)]")
    encashment_bank_id = fields.Many2one('res.bank', string='Encashment Bank', tracking=17, domain="[('is_cash_incentive_bank', '=', True)]")
    encashment_date = fields.Date(string='Encashment Date', default=fields.Date.context_today)
    swift_currency_id = fields.Many2one("res.currency", string="Currency")
    erq_bank_id = fields.Many2one('res.bank', string='ERQ Bank', domain="[('is_cash_incentive_bank', '=', True)]")

    journal_id = fields.Many2one('account.journal', string='Journal')
    partner_cr_acc_id = fields.Many2one('account.account', 'Credit Account',
                                        related='partner_id.property_account_receivable_id')

    #bank_cash_dr_acc_id = fields.Many2one('account.account')

    # comment-for-upgrade
    # encashment_acc_id = fields.Many2one('account.account', 'Encashment (Dr.)',
    #                                     domain="[('user_type_id.type', '!=', 'view')]")
    # bank_charge_acc_id = fields.Many2one('account.account', 'Bank Charge (Dr.)',
    #                                      domain="[('user_type_id.type', '!=', 'view')]")
    encashment_acc_id = fields.Many2one('account.account', 'Encashment (Dr.)')
    bank_charge_acc_id = fields.Many2one('account.account', 'Bank Charge (Dr.)')


    fc_gain_loss_acc_id = fields.Many2one('account.account', 'Foreign Exchange Gain/Loss')

    invoice_line_ids = fields.Many2many('cash.incentive.invoice', string='Invoices', tracking=18)
    invoice_amt = fields.Float(string='Invoice Amount (FC)', digits=(16, 2))
    invoice_amt_bdt = fields.Float(string='Invoice Amount (BDT)', digits=(16, 2))

    encashment_rate_amnt = fields.Float(string='Encashable Amount (BDT)', digits=(16, 2))
    encashment_rate_bdt = fields.Float(string='Encashment Rate', digits=(16, 4))

    swift_amt = fields.Float(string='SWIFT Amount (FC)', digits=(16, 2))

    inter_bank_rate_bdt = fields.Float(string='Inter-Bank Rate (BDT)', digits=(16, 4))

    encashment_charge = fields.Float(string='Bank Charge (FC)', digits=(16, 2))
    encashment_charge_bdt = fields.Float(string='Bank Charge (BDT)', digits=(16, 2))
    difference_amnt_bdt = fields.Float(string='Foreign Exchange Gain/Loss (BDT)', digits=(16, 2))

    #swift_rate_bdt = fields.Float(string='SWIFT Rate (BDT)', digits=(16, 2), default=0)

    # bank_charge = fields.Float(string='Bank Charge (FC)', digits=(16, 2))
    # other_charge = fields.Float(string='Other Charge (FC)', digits=(16, 2))

    remaining_swift_amount = fields.Float(string='Remaining SWIFT Amount (FC)', tracking=6)
    remaining_swift_amount_bdt = fields.Float(string='Remaining SWIFT Amount (BDT)', tracking=6)

    is_erq_applicable = fields.Boolean(string='Is ERQ Applicable?', default=False)
    erq_percentage = fields.Float(string='ERQ Percentage', digits=(16, 4))
    bdt_encashment_percentage = fields.Float(string='BDT Encashment Percentage', digits=(16, 4))
    erq_amount_fc = fields.Float(string='ERQ Amount (FC)', digits=(16, 2))
    fc_encashment_amount = fields.Float(string='Encashment Amount (FC) ', digits=(16, 2))
    erq_amount_bdt = fields.Float(string='ERQ Amount (BDT)', digits=(16, 2))
    bdt_encashment_amount = fields.Float(string='Encashment Amount (BDT) ', digits=(16, 2))
    type = fields.Char()

    # comment_for_upgrade
    # erq_acc_id = fields.Many2one('account.account', 'ERQ (Dr.)', domain="[('user_type_id.type', '!=', 'view')]")
    erq_acc_id = fields.Many2one('account.account', 'ERQ (Dr.)')


    # other_charge_acc_id = fields.Many2one('account.account', 'Other Charge (Dr.)',
    #                                       domain="[('user_type_id.type', '!=', 'view')]")



    # invoice_line_ids = fields.One2many('journal.wizard.line', 'head_id', string='Invoices', tracking=18)

    @api.model
    def default_get(self, fields):
        res = super(JournalWizard, self).default_get(fields)
        swift_id = self.env.context.get('swift_id')
        multiple = self.env.context.get('multiple')
        if multiple == '1':
            invoice_amt = 0
            invoice_amt_bdt = 0
            difference_amnt_bdt = 0
            swift_amt = 0
            all_inv = self.env['cash.incentive.invoice'].search([('swift_message_id', 'in', swift_id)])
            swift_obj=None
            for data in swift_id:
                swift_obj = self.env['swift.message'].sudo().browse(data)
                invoice_amt += swift_obj.invoice_amt
                invoice_amt_bdt += swift_obj.invoice_amt_bdt
                difference_amnt_bdt += swift_obj.difference_amnt_bdt
                partner_id = swift_obj.partner_id.id
                swift_amt += swift_obj.swift_amt
            res['invoice_amt'] = invoice_amt
            res['invoice_amt_bdt'] = invoice_amt_bdt
            res['difference_amnt_bdt'] = difference_amnt_bdt
            res['swift_amt'] = swift_amt
            res['partner_id'] = partner_id

            res['encashment_rate_bdt'] = self.env.context.get('encashment_rate_bdt')
            res['encashment_rate_amnt'] = self.env.context.get('encashment_rate_amnt')

            res['encashment_charge'] = self.env.context.get('encashment_charge')
            res['encashment_charge_bdt'] = self.env.context.get('encashment_charge_bdt')

            # res['bank_charge'] = self.env.context.get('bank_charge')
            # res['other_charge'] = self.env.context.get('other_charge')
            #res['swift_rate_bdt'] = self.env.context.get('swift_rate_bdt')

            res['remaining_swift_amount'] = self.env.context.get('remaining_swift_amount')
            res['remaining_swift_amount_bdt'] = self.env.context.get('remaining_swift_amount_bdt')

            res['is_erq_applicable'] = self.env.context.get('is_erq_applicable')
            res['erq_percentage'] = self.env.context.get('erq_percentage')
            res['bdt_encashment_percentage'] = self.env.context.get('bdt_encashment_percentage')
            res['erq_amount_fc'] = self.env.context.get('erq_amount_fc')
            res['fc_encashment_amount'] = self.env.context.get('fc_encashment_amount')
            res['erq_amount_bdt'] = self.env.context.get('erq_amount_bdt')
            res['bdt_encashment_amount'] = self.env.context.get('bdt_encashment_amount')

            res['bank_id'] = self.env.context.get('bank_id')
            res['swift_currency_id'] = self.env.context.get('currency_id')
            res['type'] = multiple

            res['encashment_bank_id'] = self.env.context.get('encashment_bank_id')
            print('111',self.env.context.get('erq_bank_id'))
            res['erq_bank_id'] = self.env.context.get('erq_bank_id')
            print('222')
            res['encashment_date'] = self.env.context.get('encashment_date')
            res['inter_bank_rate_bdt'] = self.env.context.get('inter_bank_rate_bdt')
            print('333')
            if res['encashment_bank_id'] and res['swift_currency_id']:
                print('444')
                if not res['erq_bank_id']:
                    erq_row = self.env['cash.incentive.bank.erq'].search([('head_id', '=', res['encashment_bank_id']), ('currency_id', '=', res['swift_currency_id'])], limit=1)
                else:
                    erq_row = self.env['cash.incentive.bank.erq'].search([('head_id', '=', res['erq_bank_id']), ('currency_id', '=', res['swift_currency_id'])], limit=1)
                if erq_row:
                    res['erq_acc_id'] = erq_row.erq_acc_id.id
            print('5555')
            if swift_obj:
                print('666')
                res['encashment_acc_id'] = swift_obj.encashment_bank_id.encashment_acc_id.id if swift_obj.encashment_bank_id.encashment_acc_id else None
            print('777')

        else:
            print('888')
            all_inv = self.env['cash.incentive.invoice'].search([('swift_message_id', '=', swift_id)])
            swift_id_obj = self.env['swift.message'].sudo().browse(swift_id)
            res['partner_id'] = swift_id_obj.partner_id.id
            res['swift_id'] = swift_id_obj.id
            res['encashment_bank_id'] = swift_id_obj.encashment_bank_id.id if swift_id_obj.encashment_bank_id else None
            res['encashment_date'] = swift_id_obj.encashment_date
            res['bank_id'] = swift_id_obj.bank_id.id if swift_id_obj.bank_id else None
            res['swift_currency_id'] = swift_id_obj.currency_id.id if swift_id_obj.currency_id else None
            res['invoice_amt'] = swift_id_obj.invoice_amt
            res['invoice_amt_bdt'] = swift_id_obj.invoice_amt_bdt

            res['encashment_rate_bdt'] = swift_id_obj.encashment_rate_bdt
            res['encashment_rate_amnt'] = swift_id_obj.encashment_rate_amnt

            res['encashment_charge'] = swift_id_obj.encashment_charge
            res['encashment_charge_bdt'] = swift_id_obj.encashment_charge_bdt

            res['difference_amnt_bdt'] = swift_id_obj.difference_amnt_bdt
            res['swift_amt'] = swift_id_obj.swift_amt
            res['journal_id'] = swift_id_obj.encashment_bank_id.journal_id.id if swift_id_obj.encashment_bank_id.journal_id else None

            res['encashment_acc_id'] = swift_id_obj.encashment_bank_id.encashment_acc_id.id if swift_id_obj.encashment_bank_id.encashment_acc_id else None
            res['bank_charge_acc_id'] = swift_id_obj.encashment_bank_id.bank_charge_acc_id.id if swift_id_obj.encashment_bank_id.bank_charge_acc_id else None
            # res['other_charge_acc_id'] = swift_id_obj.encashment_bank_id.other_charge_acc_id.id if swift_id_obj.encashment_bank_id.other_charge_acc_id else None

            res['is_erq_applicable'] = swift_id_obj.is_erq_applicable
            res['inter_bank_rate_bdt'] = swift_id_obj.inter_bank_rate_bdt
            res['erq_percentage'] = swift_id_obj.erq_percentage
            res['bdt_encashment_percentage'] = swift_id_obj.bdt_encashment_percentage
            res['erq_amount_fc'] = swift_id_obj.erq_amount_fc
            res['fc_encashment_amount'] = swift_id_obj.fc_encashment_amount
            res['erq_amount_bdt'] = swift_id_obj.erq_amount_bdt
            res['bdt_encashment_amount'] = swift_id_obj.bdt_encashment_amount

            if swift_id_obj.encashment_bank_id and swift_id_obj.currency_id:
                if not swift_id_obj.erq_bank_id:
                    erq_row = self.env['cash.incentive.bank.erq'].search([('head_id', '=', swift_id_obj.encashment_bank_id.id),('currency_id', '=', swift_id_obj.currency_id.id)], limit=1)
                else:
                    erq_row = self.env['cash.incentive.bank.erq'].search([('head_id', '=', swift_id_obj.erq_bank_id.id),('currency_id', '=', swift_id_obj.currency_id.id)], limit=1)
                if erq_row:
                    res['erq_acc_id'] = erq_row.erq_acc_id.id
        print('999')
        gain_loss_acc = self.env['account.account'].search([('is_foreign_gain_loss_acc', '=', True)], limit=1)
        all_inv_ids = [x.id for x in all_inv]

        res['invoice_line_ids'] = all_inv_ids
        res['fc_gain_loss_acc_id'] = gain_loss_acc.id
        print('1000')
        return res

    def action_create_journal(self):
        # Invoice Receivable Credit line
        invoice_line1 = []

        bank_charge_des = 'Bank Charge has been adjusted with the invoices- '
        bank_charge_inv = ''
        erq_des_inv = ''
        t_dr = 0
        t_cr = 0
        for rec in self.invoice_line_ids:
            inv_des = 'Inv.Ref:'+rec.invoice_id.ref+'; '+str(rec.currency_id.name or '-') +' '+str(rec.total_swift_amt or '-') +' @ '+str(round(rec.usd_rate, 4) or '-')+'Tk.'
            if rec.swift_charge_fc > 0:
                if bank_charge_inv == '':
                    bank_charge_inv = rec.invoice_id.ref + '- ' + str(rec.currency_id.name or '-') +' '+ str(rec.swift_charge_fc)
                else:
                    bank_charge_inv += ', ' + rec.invoice_id.ref + '- ' + str(rec.currency_id.name or '-') +' '+ str(rec.swift_charge_fc)

            if rec.erq_amt_fc > 0:
                if erq_des_inv == '':
                    erq_des_inv = rec.invoice_id.ref + '- ' + str(rec.erq_amt_fc or '-')
                else:
                    erq_des_inv += ', ' + rec.invoice_id.ref + '- ' + str(rec.erq_amt_fc or '-')

            #-----
            moveLineData = {
                'account_id': self.partner_cr_acc_id.id,
                'credit': round(rec.total_swift_amt_bdt, 2),
                'debit': 0,
                'name': inv_des,
                'partner_id': self.partner_id.id,
            }
            t_cr += round(rec.total_swift_amt_bdt, 2)
            invoice_line1.append((0, 0, moveLineData))
            #print(inv_des+'=credit='+ str(rec.total_swift_amt_bdt))
        bank_charge_des = bank_charge_des + bank_charge_inv

        # ERQ applicable lines
        if self.swift_id.is_erq_applicable:
            # ERQ Encashment line
            if self.swift_id.bdt_encashment_amount > 0:
                if not self.encashment_acc_id:
                    raise ValidationError(_('Encashment Account Mandatory.'))
                encash_des = 'Encashment Amount; ' + str(self.swift_id.currency_id.name or '-') +' '+ str(
                    self.swift_id.fc_encashment_amount or '-') + ' @ ' + str(
                    round(self.swift_id.encashment_rate_bdt, 4) or '-') + 'Tk.'

                moveLineData6 = {
                    'account_id': self.encashment_acc_id.id,
                    'debit': round(self.swift_id.bdt_encashment_amount, 2),
                    'credit': 0,
                    'name': encash_des,
                    'partner_id': self.partner_id.id,
                }
                t_dr += round(self.swift_id.bdt_encashment_amount, 2)
                invoice_line1.append((0, 0, moveLineData6))
                #print(encash_des + '=debit=' + str(self.swift_id.bdt_encashment_amount))
            # ERQ line
            if self.swift_id.erq_amount_bdt > 0:
                if not self.erq_acc_id:
                    raise ValidationError(_('ERQ Account Mandatory.'))
                #---------- ERQ
                erq_des = 'ERQ Amount; ' + str(self.swift_id.currency_id.name or '-') +' '+ str(
                    self.swift_id.erq_amount_fc or '-') +' @ '+str(round(self.swift_id.inter_bank_rate_bdt, 4) or '-') +'Tk.'
                if erq_des_inv:
                    erq_des += ' ('+erq_des_inv+')'

                moveLineData5 = {
                    'account_id': self.erq_acc_id.id,
                    'debit': round(self.swift_id.erq_amount_bdt, 2),
                    'credit': 0,
                    'name': erq_des,
                    'partner_id': self.partner_id.id,
                }
                t_dr += round(self.swift_id.erq_amount_bdt, 2)
                invoice_line1.append((0, 0, moveLineData5))
                #print(erq_des + '=debit=' + str(self.swift_id.erq_amount_bdt))

        else:
            if self.swift_id.encashment_rate_amnt > 0:
                if not self.encashment_acc_id:
                    raise ValidationError(_('Bank Journal Debit Account Mandatory.'))
                encash_des = 'Encashment Amount; ' + str(self.swift_id.currency_id.name or '-') +' '+ str(
                    self.swift_id.swift_amt or '-') + ' @ ' + str(
                    round(self.swift_id.encashment_rate_bdt, 4) or '-') + 'Tk.'

                moveLineData1 = {
                    'account_id': self.encashment_acc_id.id,
                    'debit': round(self.swift_id.encashment_rate_amnt, 2),
                    'credit': 0,
                    'name': encash_des,
                    'partner_id': self.partner_id.id,
                }
                t_dr += round(self.swift_id.encashment_rate_amnt, 2)
                invoice_line1.append((0, 0, moveLineData1))
                #print(encash_des + '=debit=' + str(self.swift_id.encashment_rate_amnt))

        # ------- BANK Charge line
        if self.swift_id.encashment_charge_bdt > 0:
            if not self.bank_charge_acc_id:
                raise ValidationError(_('Bank Charge Account Mandatory.'))

            # charge_des = 'Bank Charge; ' + str(self.swift_id.currency_id.name or '-') + str(
            #     self.swift_id.encashment_charge or '-')

            moveLineData2 = {
                'account_id': self.bank_charge_acc_id.id,
                'debit': round(self.swift_id.encashment_charge_bdt, 2),
                'credit': 0,
                'name': bank_charge_des,
                'partner_id': self.partner_id.id,
            }
            t_dr += round(self.swift_id.encashment_charge_bdt, 2)
            invoice_line1.append((0, 0, moveLineData2))
            #print(charge_des + '=debit=' + str(self.swift_id.encashment_charge_bdt))

        # Gain/Loss - differance
        if self.swift_id.difference_amnt_bdt or self.swift_id.difference_amnt_bdt != 0:
            if not self.fc_gain_loss_acc_id:
                raise ValidationError(_('Foreign Gain/Loss Account Mandatory.'))

            if self.swift_id.difference_amnt_bdt > 0:
                diff_amount = self.swift_id.difference_amnt_bdt
                cr_acc = self.fc_gain_loss_acc_id.id
                moveLineData7 = {
                    'account_id': cr_acc,
                    'debit': 0,
                    'credit': round(diff_amount, 2),
                    'name': 'Foreign Exchange Gain',
                    'partner_id': None,
                }
                t_cr += round(diff_amount, 2)
                invoice_line1.append((0, 0, moveLineData7))
                #print('Difference Amount cr' + '=credit=' + str(diff_amount))
            else:
                diff_amount = (-1) * self.swift_id.difference_amnt_bdt
                dr_acc = self.fc_gain_loss_acc_id.id
                moveLineData6 = {
                    'account_id': dr_acc,
                    'debit': round(diff_amount, 2),
                    'credit': 0,
                    'name': 'Foreign Exchange Loss',
                    'partner_id': None,
                }
                t_dr += round(diff_amount, 2)
                invoice_line1.append((0, 0, moveLineData6))
                #print('Difference Amount dr' + '=debit=' + str(diff_amount))
        # print(invoice_line1)
        # print(t_dr)
        # print(t_cr)
        if t_cr > t_dr:
            dif = t_cr - t_dr
            for rec in invoice_line1:
                if rec[2]['debit'] > 0:
                    rec[2]['debit'] += float("{0:.2f}".format(dif))
                    break
        if t_dr > t_cr:
            dif = t_dr - t_cr
            for rec in invoice_line1:
                if rec[2]['credit'] > 0:
                    rec[2]['credit'] += float("{0:.2f}".format(dif))
                    break
        # rint(invoice_line1)
        inv_data2 = self.env['account.move'].create({
            'invoice_origin': '',
            'partner_id': self.partner_id.id,
            'invoice_date_due': fields.Date.today(),
            'type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.swift_id.encashment_date,
            'line_ids': invoice_line1
        })
        inv_data2.post()
        self.swift_id.move_id = inv_data2.id

        # Invoice payment ---------------
        if self.invoice_line_ids:
            for rec in self.invoice_line_ids:
                if rec.encashment_amt_bdt > 0:
                    net_amount = rec.invoice_id.amount_residual - rec.encashment_amt_bdt
                    paid_amount = rec.invoice_id.amount_total - rec.invoice_id.amount_residual
                    total_amount = paid_amount + rec.encashment_amt_bdt
                    if rec.encashment_amt_bdt >= rec.invoice_id.amount_residual:
                        total_amount = rec.invoice_id.amount_residual
                        net_amount = 0
                    rec.invoice_id.amount_residual_signed = net_amount  # due
                    rec.invoice_id.amount_residual = net_amount

                    if rec.invoice_id.type == 'out_invoice':
                        if rec.invoice_id.payment_amount > 0:
                            rec.invoice_id.payment_amount += total_amount
                        else:
                            rec.invoice_id.payment_amount = total_amount

                    if rec.invoice_id.invoice_payment_amount_fc > 0:
                        amount = rec.swift_amt + rec.swift_charge_fc
                        rec.invoice_id.invoice_payment_amount_fc += amount
                    else:
                        amount = rec.swift_amt + rec.swift_charge_fc
                        rec.invoice_id.invoice_payment_amount_fc = amount

                    if rec.invoice_id.amount_residual < 1:
                        rec.invoice_id.invoice_payment_state = 'paid'

        self.swift_id.is_journal_created = True
        self.swift_id.state = 'pay'
        #-------------------
        self.swift_id.partner_cr_acc_id = self.partner_cr_acc_id.id or None
        self.swift_id.encashment_acc_id = self.encashment_acc_id.id or None
        self.swift_id.bank_charge_acc_id = self.bank_charge_acc_id.id or None
        self.swift_id.fc_gain_loss_acc_id = self.fc_gain_loss_acc_id.id or None
        self.swift_id.erq_acc_id = self.erq_acc_id.id
        self.swift_id.date_credited_beneficiaries = self.encashment_date
        self.swift_id.onchange_date_credited_beneficiaries()

        # self.swift_id.encashment_date = self.encashment_date

    def action_create_journal_multiple(self):
        # 1st journal for invoice
        invoice_line1 = []
        for rec in self.invoice_line_ids:
            inv_des = 'Inv.Ref:' + rec.invoice_id.ref + ';' + str(rec.currency_id.name or '-') + str(
                rec.swift_amt or '-') + '@' + str(round(rec.usd_rate, 4) or '-') + 'Tk.'
            moveLineData = {
                'account_id': self.partner_cr_acc_id.id,
                'credit': rec.total_swift_amt_bdt,
                'debit': 0,
                'name': inv_des,
                'partner_id': self.partner_id.id,
            }
            invoice_line1.append((0, 0, moveLineData))

        # remaining swift amont line
        # ERQ applicable lines
        if self.is_erq_applicable:
            # ERQ Encashment line
            if self.bdt_encashment_amount > 0:
                if not self.encashment_acc_id:
                    raise ValidationError(_('Bank Journal Debit Account Mandatory.'))
                encash_des = 'Encashment Amount; ' + str(self.swift_currency_id.name or '-') + str(
                    self.fc_encashment_amount or '-') + '@' + str(
                    round(self.inter_bank_rate_bdt, 4) or '-') + 'Tk.'
                moveLineData1 = {
                    'account_id': self.encashment_acc_id.id,
                    'debit': self.bdt_encashment_amount,
                    'credit': 0,
                    'name': encash_des,
                    'partner_id': self.partner_id.id,
                }
                invoice_line1.append((0, 0, moveLineData1))

            # ERQ line
            if self.erq_amount_bdt > 0:
                if not self.erq_acc_id:
                    raise ValidationError(_('ERQ Account Mandatory.'))
                # ---------- ERQ
                erq_des = 'ERQ Amount; ' + str(self.swift_id.swift_currency_id.name or '-') + str(
                    self.swift_id.erq_amount_fc or '-') + '@' + str(round(self.swift_id.inter_bank_rate_bdt, 4) or '-') + 'Tk.'
                moveLineData5 = {
                    'account_id': self.erq_acc_id.id,
                    'debit': self.erq_amount_bdt,
                    'credit': 0,
                    'name': erq_des,
                    'partner_id': self.partner_id.id,
                }
                invoice_line1.append((0, 0, moveLineData5))

        else:
            if self.encashment_rate_amnt > 0:
                if not self.encashment_acc_id:
                    raise ValidationError(_('Bank Journal Debit Account Mandatory.'))
                encash_des = 'Encashment Amount; ' + str(self.swift_currency_id.name or '-') + str(
                    self.swift_amt or '-') + '@' + str(
                    round(self.encashment_rate_bdt, 4) or '-') + 'Tk.'

                moveLineData1 = {
                    'account_id': self.encashment_acc_id.id,
                    'debit': self.encashment_rate_amnt,
                    'credit': 0,
                    'name': encash_des,
                    'partner_id': self.partner_id.id,
                }
                invoice_line1.append((0, 0, moveLineData1))

        # bank_charge amont line
        if self.encashment_charge_bdt:
            if not self.bank_charge_acc_id:
                raise ValidationError(_('Bank Charge Account Mandatory.'))
            charge_des = 'Bank Charge; ' + str(self.swift_currency_id.name or '-') + str(
                self.encashment_charge or '-')
            moveLineData2 = {
                'account_id': self.bank_charge_acc_id.id,
                'debit': self.encashment_charge_bdt,
                'credit': 0,
                'name': charge_des,
                'partner_id': self.partner_id.id,
            }
            invoice_line1.append((0, 0, moveLineData2))

        # if difference amount
        if self.difference_amnt_bdt or self.difference_amnt_bdt != 0:
            if not self.fc_gain_loss_acc_id:
                raise ValidationError(_('Foreign Gain/Loss Account Mandatory.'))

            if self.difference_amnt_bdt > 0:
                diff_amount = self.difference_amnt_bdt
                cr_acc = self.fc_gain_loss_acc_id.id
                moveLineData7 = {
                    'account_id': cr_acc,
                    'debit': 0,
                    'credit': diff_amount,
                    'name': 'Difference Amount Cr',
                    'partner_id': None,
                }
                invoice_line1.append((0, 0, moveLineData7))
            else:
                diff_amount = (-1) * self.difference_amnt_bdt
                dr_acc = self.fc_gain_loss_acc_id.id
                moveLineData6 = {
                    'account_id': dr_acc,
                    'debit': diff_amount,
                    'credit': 0,
                    'name': 'Difference Amount Dr',
                    'partner_id': None,
                }
                invoice_line1.append((0, 0, moveLineData6))
        inv_data2 = self.env['account.move'].create({
            'invoice_origin': '',
            'partner_id': self.partner_id.id,
            'invoice_date_due': fields.Date.today(),
            'type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.encashment_date,
            'line_ids': invoice_line1
        })
        inv_data2.post()

        # Invoice payment ---------------
        if self.invoice_line_ids:
            for rec in self.invoice_line_ids:
                if rec.encashment_amt_bdt > 0:
                    net_amount = rec.invoice_id.amount_residual - rec.encashment_amt_bdt
                    paid_amount = rec.invoice_id.amount_total - rec.invoice_id.amount_residual
                    total_amount = paid_amount + rec.encashment_amt_bdt
                    if rec.encashment_amt_bdt >= rec.invoice_id.amount_residual:
                        total_amount = rec.invoice_id.amount_residual
                        net_amount = 0
                    rec.invoice_id.amount_residual_signed = net_amount  # due
                    rec.invoice_id.amount_residual = net_amount

                    if rec.invoice_id.type == 'out_invoice':
                        if rec.invoice_id.payment_amount > 0:
                            rec.invoice_id.payment_amount += total_amount
                        else:
                            rec.invoice_id.payment_amount = total_amount

                    if rec.invoice_id.invoice_payment_amount_fc > 0:
                        amount = rec.swift_amt + rec.swift_charge_fc
                        rec.invoice_id.invoice_payment_amount_fc += amount
                    else:
                        amount = rec.swift_amt + rec.swift_charge_fc
                        rec.invoice_id.invoice_payment_amount_fc = amount

                    if rec.invoice_id.amount_residual < 1:
                        rec.invoice_id.invoice_payment_state = 'paid'

        swift_id = self.env.context.get('swift_id')
        for data in swift_id:
            swift_obj = self.env['swift.message'].sudo().browse(data)
            swift_obj.is_journal_created = True
            swift_obj.state = 'pay'
            swift_obj.move_id = inv_data2.id
            swift_obj.encashment_date = self.encashment_date


class JournalWizardLine(models.TransientModel):
    _name = "journal.wizard.line"

    head_id = fields.Many2one('journal.wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoices', required=True, ondelete='cascade')
    invoice_date = fields.Date(string='Invoice Date')
    invoice_qty_str = fields.Char(string='Quantity')
    invoice_amt = fields.Float(string='Invoice Amount')
    basis_fee_amt = fields.Float(string='Basis Fee Amount')
    swift_amt = fields.Float(string='Swift Amount')
    currency_id = fields.Many2one("res.currency", string="Currency")

    incentive_amt_fc = fields.Float(string='Incentive Amount (FC)', digits=(16, 2), compute="_compute_incentive_amt_fc")
    incentive_amt_bdt = fields.Float(string='Incentive Amount (BDT)',compute="_compute_incentive_amt_bdt")
    encashment_amt_bdt = fields.Float(string='Equivalent Amount (BDT)', digits=(16, 2), compute="_compute_encashment_amt_bdt")
    contract_number = fields.Char(string='Contract No.')
    contract_date_str = fields.Char(string='Contract Date')


