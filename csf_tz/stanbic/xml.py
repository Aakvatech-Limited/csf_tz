from pathlib import Path

import frappe
import xmltodict


def parse_xml(path):
	"""Read only Stanbic XML responses within this site's private inbox."""
	inbox = Path(frappe.get_site_path("private", "files", "stanbic", "inbox")).resolve()
	candidate = Path(path).resolve()
	if not candidate.is_relative_to(inbox) or candidate.suffix.lower() != ".xml":
		raise ValueError("Stanbic response path is outside the private inbox")
	with candidate.open(encoding="utf-8") as source:
		return xmltodict.parse(source.read())
