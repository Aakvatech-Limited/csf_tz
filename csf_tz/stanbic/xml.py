import xmltodict


def parse_xml(path):
	# nosemgrep: frappe-security-file-traversal -- path is supplied by server-side callers, not by request data
	with open(path) as f:
		xml = f.read()
	return xmltodict.parse(xml)
