from odoo import models, fields, api, _, exceptions
import re


class CashIncentiveBank(models.Model):
    _name = "res.bank"
    _inherit = ["res.bank", 'mail.thread', 'mail.activity.mixin']
    # _description = "Incentive Bank"
    # _rec_name = 'name'
    # _inherit = ['mail.thread', 'mail.activity.mixin']

    # name = fields.Char(string='Name', reuired=True, tracking=True)
    swift_code = fields.Char(string='Swift Code', tracking=True)
    routing = fields.Char(string='Routing', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    code_prefix = fields.Char(string='Master Code Prefix', tracking=True)
    code_suffix = fields.Integer(string='Master Code Next Number', default=1, tracking=True)

    #------PRC
    prc_ref_prefix = fields.Char(string='PRC Ref Prefix', tracking=True)
    prc_ref_suffix = fields.Integer(string='PRC Ref Next Number', default=1, tracking=True)
    prc_letter_description = fields.Html(string="Letter Template")

    # ------Forwarding Letter (BASIS)
    flbs_ref_prefix = fields.Char(string='Forwarding (BASIS) Ref Prefix', tracking=True)
    flbs_ref_suffix = fields.Integer(string='Forwarding (BASIS) Ref Next Number', default=1, tracking=True)
    flbs_letter_description = fields.Html(string="Letter Template")

    # ------Forwarding Letter (BANK)
    flbk_ref_prefix = fields.Char(string='Forwarding (Bank) Ref Prefix', tracking=True)
    flbk_ref_suffix = fields.Integer(string='Forwarding (Bank) Ref Next Number', default=1, tracking=True)
    flbk_letter_description = fields.Html(string="Letter Template")

    #---------
    form_ka_basis_description = fields.Html(string="Letter Template")

    form_kha_ref_prefix = fields.Char(string='Form Kha Ref Prefix', tracking=True)
    form_kha_ref_suffix = fields.Integer(string='Form Kha Ref Next Number', default=1, tracking=True)
    form_kha_basis_description = fields.Html(string="Letter Template")

    form_c_description = fields.Html(string="Letter Template")
    form_ga_description = fields.Html(string="Letter Template")
    form_gha_description = fields.Html(string="Letter Template")

    encashment_forwarding_letter = fields.Html(string="Forwarding Letter")

    # swift_letter_description = fields.Html(string="Description")
    # comment-for-upgrade
    # bank_charge_acc_id = fields.Many2one('account.account', 'Bank Charge Account (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # encashment_charge_acc_id = fields.Many2one('account.account', 'SWIFT Charge Account (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # other_charge_acc_id = fields.Many2one('account.account', 'Other Charge Account (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # erq_acc_id = fields.Many2one('account.account', 'ERQ Accounts (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # encashment_acc_id = fields.Many2one('account.account', 'Encashment Account (Dr.)', domain="[('user_type_id.type', '!=', 'view')]", tracking=True)
    # journal_id = fields.Many2one('account.journal', string='Encashment Journal', tracking=True)

    bank_charge_acc_id = fields.Many2one('account.account', 'Bank Charge Account (Dr.)', tracking=True)
    encashment_charge_acc_id = fields.Many2one('account.account', 'SWIFT Charge Account (Dr.)', tracking=True)
    other_charge_acc_id = fields.Many2one('account.account', 'Other Charge Account (Dr.)', tracking=True)
    erq_acc_id = fields.Many2one('account.account', 'ERQ Accounts (Dr.)', tracking=True)
    encashment_acc_id = fields.Many2one('account.account', 'Encashment Account (Dr.)', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Encashment Journal', tracking=True)

    erq_line_ids = fields.One2many('cash.incentive.bank.erq', 'head_id', string='ERQ Lines', tracking=True)
    is_cash_incentive_bank = fields.Boolean(string='Is Cash Incentive Bank', default=False, tracking=True)
    def write(self, vals):
        if vals.get('prc_letter_description') and self.prc_letter_description:
            self.message_post(subject="----------------------------OLD--------------------------------" + self.prc_letter_description + "------------------------NEW--------------------" + vals.get('prc_letter_description'),
                              body=vals.get('prc_letter_description'))
        elif vals.get('prc_letter_description'):
            self.message_post(subject="------------------------NEW--------------------" + vals.get('prc_letter_description'),
                              body=vals.get('prc_letter_description'))


        # if vals.get('flbk_letter_description'):
        #     self.message_post(body="----------------------------OLD--------------------------------" + self.flbk_letter_description + "------------------------NEW--------------------" + vals.get('flbk_letter_description'), old_value=self.flbk_letter_description,
        #                       new_value=vals.get('flbk_letter_description'))
        # if vals.get('form_ka_basis_description'):
        #     self.message_post(body="----------------------------OLD--------------------------------" + self.form_ka_basis_description + "------------------------NEW--------------------" + vals.get('form_ka_basis_description'), old_value=self.form_ka_basis_description,
        #                       new_value=vals.get('form_ka_basis_description'))
        # if vals.get('form_kha_basis_description'):
        #     self.message_post(body="----------------------------OLD--------------------------------" + self.form_kha_basis_description + "------------------------NEW--------------------" + vals.get('form_kha_basis_description'), old_value=self.form_kha_basis_description,
        #                       new_value=vals.get('form_kha_basis_description'))
        # if vals.get('form_c_description'):
        #     self.message_post(body="----------------------------OLD--------------------------------" + self.form_c_description + "------------------------NEW--------------------" + vals.get('form_c_description'), old_value=self.form_c_description,
        #                       new_value=vals.get('form_c_description'))
        # if vals.get('form_ga_description'):
        #     self.message_post(body="----------------------------OLD--------------------------------" + self.form_ga_description + "------------------------NEW--------------------" + vals.get('form_ga_description'), old_value=self.form_ga_description,
        #                       new_value=vals.get('form_ga_description'))
        # if vals.get('form_gha_description'):
        #     self.message_post(body="----------------------------OLD--------------------------------" + self.form_gha_description + "------------------------NEW--------------------" + vals.get('form_gha_description'), old_value=self.form_gha_description,
        #                       new_value=vals.get('form_gha_description'))

        res = super(CashIncentiveBank, self).write(vals)
        return res

    @api.constrains('name')
    def _check_unique_name(self):
        envobj = self.env['res.bank']
        for rec in self:
            msg = '"%s"' % rec.name
            record = envobj.sudo().search([('id', '!=', rec.id), ('name', '=', rec.name)], limit=1)
            if record:
                raise exceptions.ValidationError("'" + msg + "' already exists!")
    # not found any field name letter_description
    # @api.constrains('letter_description')
    # def _check_letter_description_length(self):
    #     limit = 10000
    #     field_name = "Description"
    #
    #     for record in self:
    #         if record:
    #             cleanr = re.compile('<.*?>')
    #             cleantext = re.sub(cleanr, '', record)
    #             if len(cleantext) > limit:
    #                 raise exceptions.ValidationError("'" + field_name + "' can be maximum " + str(limit) + " characters!")


class CashIncentiveBankERQ(models.Model):
    _name = "cash.incentive.bank.erq"
    _description = "Cash Incentive Bank ERQ"
    _rec_name = 'currency_id'

    head_id = fields.Many2one('res.bank', ondelete='cascade', string='Incentive Bank',
                              domain="[('is_cash_incentive_bank', '=', True)]")

    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    # comment-for-upgrade
    # erq_acc_id = fields.Many2one('account.account', 'ERQ Acc', domain="[('user_type_id.type', '!=', 'view')]", required=True)
    erq_acc_id = fields.Many2one('account.account', 'ERQ Acc', required=True)

    @api.constrains('currency_id','head_id')
    def _check_unique_currency_id(self):
        for rec in self:
            envobj = self.env['cash.incentive.bank.erq']
            msg = 'Currency "%s"' % rec.currency_id.name
            records = envobj.sudo().search([('id', '!=', rec.id), ('head_id', '=', rec.head_id.id), ('currency_id', '=', rec.currency_id.id)], limit=1)
            if records:
                raise exceptions.ValidationError("'" + msg + "' already exists!")
