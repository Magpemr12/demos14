# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os import path

from lxml import objectify
from odoo.tools import misc
from odoo.tests.common import Form

from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon


class TestMxEdiFactoring(TestMxEdiCommon):

    def test_001_factoring(self):
        self.certificate._check_credentials()
        invoice = self.invoice
        invoice.company_id.sudo().name = 'YourCompany'
        invoice.action_post()
        generated_files = self._process_documents_web_services(self.invoice, {'cfdi_3_3'})
        self.assertTrue(generated_files)
        self.assertEqual(invoice.edi_state, "sent", invoice.message_ids.mapped('body'))
        factoring = invoice.partner_id.sudo().create({
            'name': 'Financial Factoring',
            'country_id': self.env.ref('base.mx').id,
            'type': 'invoice',
        })
        invoice.partner_id.sudo().commercial_partner_id.l10n_mx_edi_factoring_id = factoring.id
        # Register the payment
        ctx = {'active_model': 'account.move', 'active_ids': invoice.ids, 'force_ref': True}
        bank_journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        payment_register = Form(self.env['account.payment'].with_context(ctx))
        payment_register.date = invoice.date
        payment_register.l10n_mx_edi_payment_method_id = self.env.ref('l10n_mx_edi.payment_method_efectivo')
        payment_register.payment_method_id = self.env.ref('account.account_payment_method_manual_in')
        payment_register.journal_id = bank_journal
        payment_register.amount = invoice.amount_total
        payment_register.save().action_post()
        payment = invoice._get_reconciled_payments()
        self.assertTrue(invoice.l10n_mx_edi_factoring_id, 'Financial Factor not assigned')
        xml_expected_str = misc.file_open(path.join(
            'l10n_mx_edi_factoring', 'tests', 'expected_payment.xml')).read().encode('UTF-8')
        xml_expected = objectify.fromstring(xml_expected_str)
        xml = payment.l10n_mx_edi_get_xml_etree()
        self.xml_merge_dynamic_items(xml, xml_expected)
        xml_expected.attrib['Folio'] = xml.attrib['Folio']
        self.assertEqualXML(xml, xml_expected)
