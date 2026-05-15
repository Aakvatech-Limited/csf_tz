import xmltodict


def parse_xml(path):
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
	with open(path, "r") as f:
		xml = f.read()
	return xmltodict.parse(xml)
