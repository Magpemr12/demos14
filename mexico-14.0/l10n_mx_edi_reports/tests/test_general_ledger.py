# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os.path import join
from dateutil.relativedelta import relativedelta
from lxml import objectify
from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon
from odoo import fields
from odoo.tools import misc
from odoo.tests.common import Form


class TestJournalEntryReport(TestMxEdiCommon):

    def setUp(self):
        super().setUp()
        self.report_moves = self.env['l10n_mx.general.ledger.report']
        self.payments_model = self.env['account.payment.register']
        self.payment_obj = self.env['account.payment']
        self.journal_bank = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)
        self.date = fields.Datetime.context_timestamp(
            self.journal_bank, fields.Datetime.from_string(
                fields.Datetime.now())).replace(day=15)
        self.date = self.date - relativedelta(months=1)
        self.xml_expected_str = misc.file_open(join(
            'l10n_mx_edi_reports', 'tests', 'expected_moves.xml')
        ).read().encode('UTF-8')
        self.payment_method_manual_out = self.env.ref(
            'account.account_payment_method_manual_out')
        self.transfer = self.env.ref(
            'l10n_mx_edi.payment_method_transferencia')
        self.bank_account = self.ref(
            'account_bank_statement_import.ofx_partner_bank_1')
        journal_acc = self.env['res.partner.bank'].create({
            'acc_number': '123456789012345',
            'bank_id': self.ref('l10n_mx.acc_bank_012_BBVA_BANCOMER'),
            'partner_id': self.journal_bank.company_id.partner_id.id,
            'company_id': self.journal_bank.company_id.id,
        })
        self.journal_bank.bank_account_id |= journal_acc
        self.certificate._check_credentials()

    def test_001_get_report(self):
        self.product.taxes_id = False
        invoice = self.invoice
        invoice.currency_id = self.env.ref('base.MXN')
        invoice.invoice_date = self.date.date()
        invoice.with_context(
            check_move_validity=False)._onchange_invoice_date()
        invoice.action_post()
        generated_files = self._process_documents_web_services(invoice, {'cfdi_3_3'})
        self.assertTrue(generated_files)
        payment = self.generate_payment(invoice)
        payment2 = self.generate_payment(invoice)
        payment2.write({
            'l10n_mx_edi_payment_method_id': self.transfer.id,
            'partner_bank_id': self.bank_account,
        })
        options = self.report_moves._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.report_moves.get_xml(options)
        xml = objectify.fromstring(data)
        xml.attrib['Sello'] = ''
        xml.attrib['Certificado'] = ''
        xml.attrib['noCertificado'] = ''
        xml_dt = self.xml2dict(xml)
        self.xml_expected_str = self.xml_expected_str.decode().format(
            concept1=invoice.name, date=date, move1=invoice.id,
            payment_date=payment.date,
            uuid2=payment.l10n_mx_edi_cfdi_uuid,
            move2=payment.move_line_ids.mapped('move_id').id,
            concept2=payment.ref,
            move3=payment2.move_line_ids.mapped('move_id').id,
            concept3=payment2.ref)
        xml_expected = objectify.fromstring(self.xml_expected_str.encode(
            'utf-8'))
        xml_expected.attrib['Mes'] = self.date.strftime('%m')
        xml_expected.attrib['Anio'] = self.date.strftime('%Y')
        xml_expected_dt = self.xml2dict(xml_expected)
        self.maxDiff = None
        self.assertEqual(xml_dt, xml_expected_dt)
        # Check the first payment
        xml.remove(xml.getchildren()[0])
        xml_expected.remove(xml_expected.getchildren()[0])
        xml_dt = self.xml2dict(xml)
        xml_expected_dt = self.xml2dict(xml_expected)
        self.assertEqual(xml_dt, xml_expected_dt)
        # Check the second payment
        xml.remove(xml.getchildren()[0])
        xml_expected.remove(xml_expected.getchildren()[0])
        xml_dt = self.xml2dict(xml)
        xml_expected_dt = self.xml2dict(xml_expected)
        self.assertEqual(xml_dt, xml_expected_dt)

    def generate_payment(self, invoice):
        # Register payment
        ctx = {'active_model': 'account.move', 'active_ids': [invoice.id]}
        payment_register = Form(self.env['account.payment'].with_context(ctx))
        payment_register.date = self.date
        payment_register.l10n_mx_edi_payment_method_id = self.env.ref('l10n_mx_edi.payment_method_efectivo')
        payment_register.payment_method_id = self.payment_method_manual_out
        payment_register.journal_id = self.journal_bank
        payment_register.amount = invoice.amount_total / 2
        payment_register.currency_id = invoice.currency_id
        payment_register.save().post()
        return invoice._get_reconciled_payments()
