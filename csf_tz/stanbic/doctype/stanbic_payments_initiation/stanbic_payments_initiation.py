# Copyright (c) 2023, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from csf_tz.stanbic.doctype.stanbic_payments_initiation.xml import get_xml
from csf_tz.stanbic.pgp import encrypt_pgp
import json


class StanbicPaymentsInitiation(Document):
    def validate(self):
        self.validate_data()

    def set_data(self):
        payroll_entry_doc = frappe.get_cached_doc("Payroll Entry", self.payroll_entry)
        self.set_entries(payroll_entry_doc)
        self.insert(ignore_permissions=True)
        self.reload()
        self.xml = get_xml(self)
        public_key, file_code = frappe.get_cached_value(
            "Stanbic Setting", self.stanbic_setting, ["pgp_public_key", "file_code"]
        )
        self.file_code = file_code
        self.encrypted_xml = encrypt_pgp(self.xml, public_key)
        self.save(ignore_permissions=True)

    def set_entries(self, payroll_entry_doc=None):
        if not payroll_entry_doc:
            payroll_entry_doc = frappe.get_cached_doc(
                "Payroll Entry", self.payroll_entry
            )
        self.number_of_transactions = 0
        self.control_sum = 0
        self.stanbic_payments_info = []
        # get all salay slips
        salary_slips = self.get_salary_slips()
        for slip in salary_slips:
            entry = self.append("stanbic_payments_info", {})
            entry.salary_slip = slip.name
            entry.employee = slip.employee
            entry.transfer_currency = slip.currency
            entry.transfer_amount = slip.net_pay
            self.number_of_transactions += 1
            self.control_sum += slip.net_pay

    def validate_data(self):
        self.validate_entries(self.payroll_entry)

    def validate_entries(self, payroll_entry_doc=None):
        # to be add validation as it required
        pass

    def get_salary_slips(self):
        slips = frappe.get_all(
            "Salary Slip",
            filters={"payroll_entry": self.payroll_entry, "docstatus": ["in", [0, 1]]},
            fields=[
                "name",
                "employee",
                "employee_name",
                "company",
                "docstatus",
                "currency",
                "net_pay",
            ],
        )
        # check if all slips are submitted
        for slip in slips:
            if slip.docstatus == 0:
                frappe.throw(
                    "Salary Slip {0} is not submitted".format(slip.name),
                    title="Salary Slip Not Submitted",
                )
        return slips

    def on_submit(self):
        import os
        from csf_tz.stanbic.sftp import get_absolute_path
        from frappe.utils import now, format_datetime

        timestamp = format_datetime(now(), "yyyyMMddHHmmss") + "000"
        filename = f"WASCO_H2H_Pain001v3_TZ_{self.file_code}_{timestamp}.xml"
        create_path = get_absolute_path("/private/files/stanbic/outbox")
        file_path = os.path.join(create_path, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as file:
            file.write(self.encrypted_xml)

    def on_update_after_submit(self):
        if self.stanbic_ack_change and self.stanbic_ack:
            ack_dict = json.loads(self.stanbic_ack)
            stanbic_ack_status = ack_dict["Document"]["CstmrPmtStsRpt"][
                "OrgnlGrpInfAndSts"
            ]["GrpSts"]
            if ack_dict["Document"]["CstmrPmtStsRpt"]["OrgnlGrpInfAndSts"].get(
                "StsRsnInf"
            ):
                stanbic_ack_status = (
                    stanbic_ack_status
                    + " "
                    + ack_dict["Document"]["CstmrPmtStsRpt"]["OrgnlGrpInfAndSts"][
                        "StsRsnInf"
                    ]["AddtlInf"]
                )

            frappe.db.set_value(
                "Stanbic Payments Initiation",
                self.name,
                "stanbic_ack_status",
                stanbic_ack_status,
            )
            frappe.db.set_value(
                "Stanbic Payments Initiation",
                self.name,
                "stanbic_ack_change",
                0,
            )
        if self.stanbic_intaud_change and self.stanbic_intaud:
            ack_dict = json.loads(self.stanbic_intaud)
            TxInfAndSts = ack_dict["Document"]["CstmrPmtStsRpt"]["OrgnlPmtInfAndSts"][
                "TxInfAndSts"
            ]
            if not isinstance(TxInfAndSts, list):
                TxInfAndSts = [TxInfAndSts]
            for OrgnlEndToEndId in TxInfAndSts:
                try:
                    sal_slip_doc = frappe.get_doc(
                        "Stanbic Payments Info",
                        {
                            "parent": self.name,
                            "salary_slip": OrgnlEndToEndId["OrgnlEndToEndId"],
                        },
                    )
                    stanbic_intaud_status = frappe.as_json(
                        OrgnlEndToEndId["StsRsnInf"]["AddtlInf"]
                        if OrgnlEndToEndId.get("StsRsnInf").get("AddtlInf")
                        else "STATUS NOT FOUND"
                    )
                    frappe.db.set_value(
                        "Stanbic Payments Info",
                        sal_slip_doc.name,
                        "stanbic_intaud_status",
                        stanbic_intaud_status,
                    )
                except Exception as e:
                    frappe.log_error(
                        f"Error in {self.name}",
                        f"Error {str(e)} {self.name} {OrgnlEndToEndId}",
                    )
            frappe.db.set_value(
                "Stanbic Payments Initiation",
                self.name,
                "stanbic_intaud_change",
                0,
            )
        if self.stanbic_finaud_change and self.stanbic_finaud:
            ack_dict = json.loads(self.stanbic_finaud)
            TxInfAndSts = ack_dict["Document"]["CstmrPmtStsRpt"]["OrgnlPmtInfAndSts"][
                "TxInfAndSts"
            ]
            if not isinstance(TxInfAndSts, list):
                TxInfAndSts = [TxInfAndSts]
            for OrgnlEndToEndId in TxInfAndSts:
                try:
                    sal_slip_doc = frappe.get_doc(
                        "Stanbic Payments Info",
                        {
                            "parent": self.name,
                            "salary_slip": OrgnlEndToEndId["OrgnlEndToEndId"],
                        },
                    )
                    stanbic_finaud_status = frappe.as_json(
                        OrgnlEndToEndId["StsRsnInf"]["AddtlInf"]
                        if OrgnlEndToEndId.get("StsRsnInf").get("AddtlInf")
                        else "STATUS NOT FOUND"
                    )
                    frappe.db.set_value(
                        "Stanbic Payments Info",
                        sal_slip_doc.name,
                        "stanbic_finaud_status",
                        stanbic_finaud_status,
                    )
                except Exception as e:
                    frappe.log_error(
                        f"Error in {self.name}",
                        f"Error {str(e)} {self.name} {str(OrgnlEndToEndId)}",
                    )
            frappe.db.set_value(
                "Stanbic Payments Initiation",
                self.name,
                "stanbic_finaud_change",
                0,
            )
