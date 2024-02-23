# coding=utf-8
from odoo import fields, models, api, exceptions, _


class IncentiveLetterWithLetterHead(models.AbstractModel):
    _name = 'report.cash_incentive.incentive_prc_letter_wo_report_qweb'

    # @api.model
    # def render_html(self, docids, data=None):
    #     report_obj = self.env['report']
    #     report = report_obj._get_report_from_name('custom_hr_employee_letters.emp_letter_report_qweb')
    #     docargs = {
    #         'doc_ids': docids,
    #         'doc_model': report.model,
    #         'docs': data['ids'],
    #     }
    #     return report_obj.render('custom_hr_employee_letters.emp_letter_report_qweb', docargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['cash.incentive.head'].browse(docids)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'cash.incentive.head',
            'data': data['ids'],
            'docs': docs,
            'with_head': data['with_head'],
            'rpt_name': data['rpt_name'],
        }


class IncentiveLetterWithLetterHeadTwo(models.AbstractModel):
    _name = 'report.cash_incentive.incentive_prc_letter_wo_report_two_qweb'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['cash.incentive.head'].browse(docids)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'cash.incentive.head',
            'data': data['ids'],
            'docs': docs,
            'with_head': data['with_head'],
            'rpt_name': data['rpt_name'],
        }


class IncentiveLetterWithoutLetterHeadForkKa(models.AbstractModel):
    _name = 'report.cash_incentive.incentive_prc_letter_wo_form_ka_qweb'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['cash.incentive.head'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'cash.incentive.head',
            'data': data['ids'],
            'docs': docs,
            'with_head': data['with_head'],
            'rpt_name': data['rpt_name'],
            'company_idjh': data['company_idjh'],
        }


class IncentiveLetterWithLetterHeadForkKa(models.AbstractModel):
    _name = 'report.cash_incentive.incentive_prc_letter_w_form_ka_qweb'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['cash.incentive.head'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'cash.incentive.head',
            'data': data['ids'],
            'docs': docs,
            'with_head': data['with_head'],
            'rpt_name': data['rpt_name'],
            'company_idjh': data['company_idjh'],
        }


class IncentiveLetterWithLetterHeadActionTree(models.AbstractModel):
    _name = 'report.cash_incentive.incentive_report_from_ree_action'

    # @api.model
    # def render_html(self, docids, data=None):
    #     report_obj = self.env['report']
    #     report = report_obj._get_report_from_name('custom_hr_employee_letters.emp_letter_report_qweb')
    #     docargs = {
    #         'doc_ids': docids,
    #         'doc_model': report.model,
    #         'docs': data['ids'],
    #     }
    #     return report_obj.render('custom_hr_employee_letters.emp_letter_report_qweb', docargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['cash.incentive.head'].browse(docids)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'cash.incentive.head',
            'data': data['ids'],
            'docs': docs,
            'with_head': data['with_head'],
            'rpt_name': data['rpt_name'],
        }


class IncentiveLetterWithOutLetterHeadActionTree(models.AbstractModel):
    _name = 'report.cash_incentive.incentive_prc_letter_without_report_qweb'

    # @api.model
    # def render_html(self, docids, data=None):
    #     report_obj = self.env['report']
    #     report = report_obj._get_report_from_name('custom_hr_employee_letters.emp_letter_report_qweb')
    #     docargs = {
    #         'doc_ids': docids,
    #         'doc_model': report.model,
    #         'docs': data['ids'],
    #     }
    #     return report_obj.render('custom_hr_employee_letters.emp_letter_report_qweb', docargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['cash.incentive.head'].browse(docids)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'cash.incentive.head',
            'data': data['ids'],
            'docs': docs,
            'with_head': data['with_head'],
            'rpt_name': data['rpt_name'],
        }


class IncentiveLetterWithOutLetterHeadActionTreePRC(models.AbstractModel):
    _name = 'report.cash_incentive.incentive_prc_letter_w_report_two_qweb'

    # @api.model
    # def render_html(self, docids, data=None):
    #     report_obj = self.env['report']
    #     report = report_obj._get_report_from_name('custom_hr_employee_letters.emp_letter_report_qweb')
    #     docargs = {
    #         'doc_ids': docids,
    #         'doc_model': report.model,
    #         'docs': data['ids'],
    #     }
    #     return report_obj.render('custom_hr_employee_letters.emp_letter_report_qweb', docargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['cash.incentive.head'].browse(docids)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'cash.incentive.head',
            'data': data['ids'],
            'docs': docs,
            'with_head': data['with_head'],
            'rpt_name': data['rpt_name'],
        }