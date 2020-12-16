from lxml import etree

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_mx_edi_create_cfdi(self):
        """If the CFDI was signed, try to adds the schemaLocation correctly"""
        result = super(AccountMove, self)._l10n_mx_edi_create_cfdi()
        cfdi = result.get('cfdi')
        if not cfdi:
            return result
        cfdi = self.l10n_mx_edi_get_xml_etree(cfdi)
        if 'implocal' not in cfdi.nsmap:
            return result
        cfdi.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = '%s %s %s' % (
            cfdi.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'),
            'http://www.sat.gob.mx/implocal',
            'http://www.sat.gob.mx/sitio_internet/cfd/implocal/implocal.xsd')
        result['cfdi'] = etree.tostring(cfdi, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        return result
