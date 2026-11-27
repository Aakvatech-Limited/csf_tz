"""Column-aware TRA PDF extraction primitives.

Keep extraction independent of Frappe so synthetic fixtures can exercise
layout variations without a database.
"""

import re
from decimal import Decimal


def declared_item_count(words):
	"""Read the count below the numbered header, ignoring other columns."""
	words = list(words)
	headers = sorted(
		(word for word in words if re.match(r"^3\.\s*No$", word["text"], re.I)),
		key=lambda word: word["top"],
	)
	if not headers:
		headers = [word for word in words if re.match(r"^3\.\s*No\s*Items$", word["text"], re.I)]
	if not headers:
		raise ValueError("Could not locate declared item count heading")
	header = headers[0]
	left = header["x0"] - 3
	right = header["x0"] + 40
	for word in words:
		if header["x0"] < word["x0"] < header["x0"] + 100 and abs(word["top"] - header["top"]) < 3:
			if re.match(r"^4\.", word["text"]):
				right = word["x0"]
				break
	candidates = [
		word for word in words
		if left <= word["x0"] < right
		and 2 < word["top"] - header["top"] <= 23
		and re.fullmatch(r"[1-9]\d{0,3}", word["text"])
	]
	if len(candidates) != 1:
		raise ValueError("Could not unambiguously read declared item count")
	return int(candidates[0]["text"])


def verify_item_numbers(count, numbers):
	"""Require the declared count and actual sequential item sections to agree."""
	if sorted(numbers) != list(range(1, count + 1)):
		raise ValueError("Declared item count differs from extracted item sections")


def tax_number(value):
	"""Blank tax cells represent zero; never reinterpret printed rates."""
	value = str(value or "").strip().replace(",", "")
	return Decimal(value) if value else Decimal(0)


def inspect_pdf(stream):
	"""Read PDF identity and item count; not a full assessment importer."""
	import pdfplumber

	with pdfplumber.open(stream) as pdf:
		if not pdf.pages or len(pdf.pages) > 100:
			raise ValueError("Unsupported PDF page count")
		first = pdf.pages[0]
		first_text = first.extract_text() or ""
		if not re.search(r"Tanzania Revenue Authority", first_text, re.I):
			raise ValueError("Not a recognized TRA document")
		count = declared_item_count(first.extract_words())
		numbers = []
		for page in pdf.pages:
			numbers.extend(int(n) for n in re.findall(r"\bItem\s+No\.?\s*(\d+)\b", page.extract_text() or "", re.I))
		verify_item_numbers(count, numbers)
		return {"number_of_items": count, "item_numbers": numbers}
