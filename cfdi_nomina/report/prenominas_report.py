# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

tipo_cuenta_dict = {
    '01': '01 Efectivo',
    '02': '02 Cheque nominativo',
    '03': '03 Transferencia electrónica de fondos',
}


class NominasReport(models.AbstractModel):
    _name = 'report.cfdi_nomina.reporte_prenominas'

    # total_p = fields.Float(string="Total P")
    # total_isr = fields.Float(string="Total Isr")
    # total_gravable = fields.Float(string="Total Taxable")
    # lines_p = fields.Char(string="lines P")
    # lines_d = fields.Char(string="lines D")
    # lines_o = fields.Char(string="Others")
    # otras_p = fields.Char(string="Others P")
    # otras_d = fields.Char(string="Others D")
    # total_subsidio_empleo = fields.Float(string="Total employment subsidy")
    # dias_trabajados = fields.Float(string="Days Worked")
    # horas_trabajados = fields.Float(string="Hours Worked")
    # salarioXhora = fields.Float(string="Hourly Wage")
    # total_sueldo = fields.Float(string="Total Salary")
    # total_d = fields.Float(string="Total D")
    # total_o = fields.Float(string="Total O")
    # total_imss = fields.Float(string="Total IMSS")
    # total_especie = fields.Float(string="Total Species")
    # t_efectivo = fields.Float(string="T Effective")
    # t_neto = fields.Float(string="T Net")
    # t_especie = fields.Float(string="T Species")
    # t_gravable = fields.Float(string="T Taxable")
    # t_subsidio = fields.Float(string="T Grant")
    # total_lines_p = fields.Char(string="Total lines P")
    # total_lines_o = fields.Char(string="Total Lines O")
    # total_lines_d = fields.Char(string="Total lines D")
    # totales = fields.Float(string="Total FDP")

    def calc_reglas_lines(self, o):
        p_id = self.env.ref("cfdi_nomina.catalogo_tipo_percepcion").id
        d_id = self.env.ref("cfdi_nomina.catalogo_tipo_deduccion").id
        o_id = self.env.ref("cfdi_nomina.catalogo_tipo_otro_pago").id

        total_p = total_d = total_o = total_sueldo = 0
        total_isr = total_imss = total_subsidio_empleo = total_especie = 0
        total_gravable = 0

        lines_p = []
        lines_d = []
        lines_o = []
        for line in o.line_ids:
            if not line.appears_on_payslip or not line.total:
                continue

            if line.salary_rule_id.tipo_id.id == p_id:
                total_p += line.total
                total_gravable += line.gravado

                if line.code == 'P001':   # SUELDO':
                    total_sueldo += line.total
                lines_p.append({
                    'code': line.code,
                    'name': line.name,
                    'total': line.total,
                })

            if line.salary_rule_id.tipo_id.id == d_id:
                total_d += line.total
                if line.code == 'D001':  # 'ISR':
                    total_isr += line.total
                if line.code == 'D002':  # 'IMSS':
                    total_imss += line.total

                lines_d.append({
                    'code': line.code,
                    'name': line.name,
                    'total': line.total,
                })

            if line.salary_rule_id.tipo_id.id == o_id:
                if line.code == 'D100':   # SUBSIDIO PARA EL EMPLEO':
                    # Subsidio se pasa en negativo en el lado de deducciones
                    total_subsidio_empleo -= line.total
                    total_d -= line.total
                    lines_d.append({
                        'code': line.code,
                        'name': line.name,
                        'total': -line.total,
                    })
                    continue
                total_o += line.total
                # _logger.info("T.Otros {}, codigo:{}, {}".format(self.total_o, line.code, line.total))
                lines_o.append({
                    'code': line.code,
                    'name': line.name,
                    'total': line.total,
                })

            if line.salary_rule_id.en_especie:
                total_especie += line.total

        lines_p = lines_p
        lines_d = lines_d
        lines_o = lines_o

        otras_p = total_p - total_sueldo
        otras_d = total_d - total_isr - total_imss - total_subsidio_empleo
        total_subsidio_empleo *= -1

        data_trabajados = o.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100')
        dias_trabajados = sum(data_trabajados.mapped('number_of_days'))
        horas_trabajados = sum(data_trabajados.mapped('number_of_hours'))
        salarioXhora = total_sueldo/horas_trabajados if horas_trabajados else 0

        # Acumula lineas totales
        total_lines_p = {}
        total_lines_o = {}
        total_lines_d = {}
        for l in lines_p:
            code = l.get('code')
            if code in total_lines_p:
                total_lines_p[code]['total'] += l.get('total', 0)
            else:
                total_lines_p[code] = l

        for l in lines_o:
            code = l.get('code')
            if code in total_lines_o:
                total_lines_o[code]['total'] += l.get('total', 0)
            else:
                total_lines_o[code] = l

        for l in lines_d:
            code = l.get('code')
            if code in total_lines_d:
                total_lines_d[code]['total'] += l.get('total', 0)
            else:
                total_lines_d[code] = l

        # Acumula totales

        t_efectivo = total_p + total_o - total_especie - total_d
        t_neto = total_p + total_o - total_d
        # _logger.info("total P {} + Total O {} - Total D {}".format(self.total_p, self.total_o, self.total_d))
        t_especie = total_especie
        t_gravable = total_gravable
        t_subsidio = total_subsidio_empleo

        # Acumula total efectivo por Forma de Pago
        fdp = o.employee_id.tipo_cuenta
        totales = {}
        if fdp in totales:
            totales[fdp]['t_efectivo'] += total_p + total_o - total_especie - total_d
        else:
            totales[fdp] = {
                'fdp': tipo_cuenta_dict[fdp],
                't_efectivo':  total_p + total_o - total_especie - total_d,
            }
        return {
            'dias_trabajados': dias_trabajados, 'otras_p': otras_p, 'total_p': total_p, 'total_o': total_o,
            'total_sueldo': total_sueldo, 'total_d': total_d, 'total_especie': total_especie,
            'horas_trabajados': horas_trabajados, 'total_imss':total_imss, 'total_isr': total_isr,
            'total_subsidio_empleo': total_subsidio_empleo, 'otras_d': otras_d, 'lines_p': lines_p,
            'lines_o': lines_o, 'lines_d': lines_d, 'total_lines_p': total_lines_p, 'total_lines_o': total_lines_o,
            'total_lines_d': total_lines_d, 'totales': totales, 't_efectivo': t_efectivo, 't_neto': t_neto,
            't_gravable': t_gravable, 't_subsidio': t_subsidio, 't_especie': t_especie

        }

    # def get_total(self, o):
    #     return self

    def get_totales(self, totales_list):
        print ("jkhkh totales_list", totales_list)
        totales = {}
        for dict in totales_list:
            for main_key, val_dict in dict.items():
                if main_key not in totales:
                    totales.update({
                        main_key: val_dict
                    })
                else:
                    totales.get(main_key).update(
                        {'total': totales.get(main_key).get('t_efectivo') + val_dict.get('t_efectivo')})
        return [v for k, v in totales.items()]

    def get_totales_percepciones(self, total_lines_p_list):
        total_lines_p = {}
        for dict in total_lines_p_list:
            for main_key, val_dict in dict.items():
                if main_key not in total_lines_p:
                    total_lines_p.update({
                        main_key: val_dict
                    })
                else:
                    total_lines_p.get(main_key).update({'total': total_lines_p.get(main_key).get('total') + val_dict.get('total')})
        return [v for k, v in total_lines_p.items()]

    def get_totales_otros(self, total_lines_o_list):
        total_lines_o = {}
        for dict in total_lines_o_list:
            for main_key, val_dict in dict.items():
                if main_key not in total_lines_o:
                    total_lines_o.update({
                        main_key: val_dict
                    })
                else:
                    total_lines_o.get(main_key).update(
                        {'total': total_lines_o.get(main_key).get('total') + val_dict.get('total')})
        return [v for k, v in total_lines_o.items()]
    
    def get_totales_deducciones(self, total_lines_d_list):
        total_lines_d = {}
        for dict in total_lines_d_list:
            for main_key, val_dict in dict.items():
                if main_key not in total_lines_d:
                    total_lines_d.update({
                        main_key: val_dict
                    })
                else:
                    total_lines_d.get(main_key).update(
                        {'total': total_lines_d.get(main_key).get('total') + val_dict.get('total')})
        return [v for k, v in total_lines_d.items()]

    def get_dato_acumulado(self, o, nombre):
        dato = o.acumulado_ids.filtered(lambda l: l.name == nombre)
        dato = dato and dato.actual_nc or 0.0
        return '{:,.2f}'.format(dato)

    @api.model
    def _get_report_values(self, docids, data=None):
        print ("Context -=-=", self._context)
        run_id = False
        pay_run = False
        payslips = self.env['hr.payslip'].browse(docids)
        if payslips:
            data.update({'name': payslips[0].name,
                         'date_start': payslips[0].date_from,
                         'date_end': payslips[0].date_to})
        if 'active_model' in self._context and self._context.get('active_model') == 'hr.payslip.run':
            run_id = self._context.get('active_id')
            pay_run = self.env['hr.payslip.run'].browse(run_id)
            data.update({'name': pay_run.name,
                         'date_start': pay_run.date_start,
                         'date_end': pay_run.date_end})
            payslips = pay_run.slip_ids

        data.update(payslips=payslips)
        # self.total_lines_p = {}
        # self.total_lines_o = {}
        # self.total_lines_d = {}
        # self.totales = {}
        # self.t_neto = 0
        # self.t_especie = 0
        # self.t_gravable = 0
        # self.t_subsidio = 0
        # self.t_efectivo = 0

        return {
            'doc_ids': [run_id] if pay_run else  payslips.ids,
            'doc_model': 'hr.payslip.run' if pay_run else 'hr.payslip',
            'docs': [pay_run] if pay_run else payslips,
            'data': data,
            'float': float,
            'calc_reglas_lines': self.calc_reglas_lines,
            'get_dato_acumulado': self.get_dato_acumulado,
            'get_totales_percepciones': self.get_totales_percepciones,
            'get_totales_deducciones': self.get_totales_deducciones,
            'get_totales_otros': self.get_totales_otros,
            'get_totales': self.get_totales,
            # 'get_total': self.get_total,
        }

