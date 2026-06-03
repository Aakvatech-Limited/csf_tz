# Copyright (c) 2023, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def get_xml(doc):
	xml = get_first_xml_part(doc)
	xml += get_payments_xml_part(doc)
	xml += get_last_xml_part(doc)
	return xml


def get_first_xml_part(doc):
	settings_doc = frappe.get_cached_doc("Stanbic Setting", doc.stanbic_setting)
	part = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
	<CstmrCdtTrfInitn>
		<GrpHdr>
			<MsgId>{doc.name}</MsgId>
			<CreDtTm>{doc.modified}</CreDtTm>
			<NbOfTxs>{doc.number_of_transactions}</NbOfTxs>
			<CtrlSum>{flt(doc.control_sum, 2):.2f}</CtrlSum>
			<InitgPty>
				<Nm>{settings_doc.initiating_party_name}</Nm>
				<Id>
					<OrgId>
						<Othr>
						<Id>{settings_doc.customerid}/{settings_doc.user}</Id>
						</Othr>
					</OrgId>
				</Id>
			</InitgPty>
		</GrpHdr>
		<PmtInf>
			<PmtInfId>{doc.name}</PmtInfId>
				<PmtMtd>TRF</PmtMtd>
				<BtchBookg>true</BtchBookg>
			<PmtTpInf>
				<InstrPrty>NORM</InstrPrty>
				<LclInstrm>
					<Prtry>AVAIL</Prtry>
				</LclInstrm>
				<CtgyPurp>
					<Prtry>61</Prtry>
				</CtgyPurp>
			</PmtTpInf>
			<ReqdExctnDt>{doc.posting_date}</ReqdExctnDt>
			<Dbtr>
				<Nm>{settings_doc.initiating_party_name}</Nm>
				<PstlAdr>
					<Ctry>{settings_doc.ordering_bank_country_code.upper()}</Ctry>
				</PstlAdr>
			</Dbtr>
			<DbtrAcct>
				<Id>
					<Othr>
						<Id>{settings_doc.ordering_customer_account_number}</Id>
					</Othr>
				</Id>
				<Tp>
					<Cd>{settings_doc.ordering_account_type}</Cd>
				</Tp>
				<Ccy>{settings_doc.ordering_account_currency}</Ccy>
			</DbtrAcct>
			<DbtrAgt>
				<FinInstnId>
					<ClrSysMmbId>
						<MmbId>{settings_doc.ordering_bank_sort_code}</MmbId>
					</ClrSysMmbId>
					<PstlAdr>
						<Ctry>{settings_doc.ordering_bank_country_code.upper()}</Ctry>
					</PstlAdr>
				</FinInstnId>
			</DbtrAgt>
			<ChrgBr>{settings_doc.charges_bearer}</ChrgBr>"""
	return part


def get_payment_part(payment):
	part = f"""<CdtTrfTxInf>
				<PmtId>
					<EndToEndId>{payment.salary_slip}</EndToEndId>
				</PmtId>
				<PmtTpInf>
					<InstrPrty>NORM</InstrPrty>
					<SvcLvl>
					</SvcLvl>
					<CtgyPurp>
						<Prtry>61</Prtry>
					</CtgyPurp>
				</PmtTpInf>
				<Amt>
					<InstdAmt Ccy="{payment.beneficiary_account_currency}">{flt(payment.transfer_amount, 2):.2f}</InstdAmt>
				</Amt>
				<CdtrAgt>
					<FinInstnId>
						<ClrSysMmbId>
							<MmbId>{payment.beneficiary_bank_sort_code}</MmbId>
						</ClrSysMmbId>
						<Nm>{payment.beneficiary_bank_name}</Nm>
						<PstlAdr>
							<Ctry>{payment.beneficiary_bank_country_code.upper() if payment.beneficiary_bank_country_code else "TZ"}</Ctry>
						</PstlAdr>
					</FinInstnId>
				</CdtrAgt>
				<Cdtr>
					<Nm>{payment.beneficiary_name}</Nm>
					<PstlAdr>
						<Ctry>{payment.beneficiary_country.upper() if payment.beneficiary_country else "TZ"}</Ctry>
					</PstlAdr>
				</Cdtr>
				<CdtrAcct>
					<Id>
						<IBAN></IBAN>
						<Othr>
							<Id>{payment.beneficiary_account_number}</Id>
						</Othr>
					</Id>
					<Tp>
						<Prtry>{payment.beneficiary_account_type}</Prtry>
					</Tp>
				</CdtrAcct>
				<RmtInf>
					<Ustrd>{payment.salary_slip}</Ustrd>
					<Strd>
						<CdtrRefInf>
							<Tp>
								<CdOrPrtry>
									<Prtry></Prtry>
								</CdOrPrtry>
							</Tp>
							<Ref>{payment.salary_slip}</Ref>
						</CdtrRefInf>
					</Strd>
				</RmtInf>
			</CdtTrfTxInf>"""

	return part


def get_payments_xml_part(doc):
	parts = ""

	for payment in doc.stanbic_payments_info:
		parts += get_payment_part(payment)

	return parts


def get_last_xml_part(doc):
	part = """</PmtInf>
	</CstmrCdtTrfInitn>
</Document>"""
	return part
