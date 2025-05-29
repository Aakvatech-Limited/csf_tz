import frappe
import requests
from bs4 import BeautifulSoup
from datetime import datetime


@frappe.whitelist(allow_guest=True)
def verify_tra_receipt(verification_code):
    """
    Verify TRA receipt and extract receipt data

    Args:
        verification_code (str): The receipt verification code (e.g., "3D89A530626_094801")

    Returns:
        dict: Contains receipt data and verification info
    """
    try:

        result = fetch_tra_verification(verification_code)

        if "error" in result:
            frappe.logger().error(f"TRA Verification error: {result['error']}")
            return {
                "success": False,
                "error": result["error"],
                "verification_code": verification_code,
            }

        receipt_data = extract_receipt_data(result["verification_data"])

        # Create TRA Tax Inv document after successful verification
        tra_tax_inv_result = create_tra_tax_inv_document(
            verification_code, receipt_data, result
        )

        return {
            "success": True,
            "verification_code": verification_code,
            "receipt_time_used": result["receipt_time_used"],
            "final_url": str(result["url"]),
            "receipt_data": receipt_data,
            "raw_verification_data": result["verification_data"],
            "timestamp": datetime.now().isoformat(),
            "tra_tax_inv": tra_tax_inv_result,
        }

    except Exception as e:
        frappe.logger().error(f"TRA Verification exception: {str(e)}")
        return {
            "success": False,
            "error": f"Verification failed: {str(e)}",
            "verification_code": verification_code,
        }


def fetch_tra_verification(verification_code):
    """
    Fetch HTML content from TRA verification by submitting the form and handling time selection

    Args:
        verification_code (str): The receipt verification code (e.g., "3D89A530626_094801")

    Returns:
        dict: Contains HTML content, parsed data, and response info
    """

    # Extract time from verification code (format: XXXXXXX_HHMMSS)
    if "_" in verification_code:
        time_part = verification_code.split("_")[1]
        if len(time_part) == 6:
            hour = time_part[:2]
            minute = time_part[2:4]
            second = time_part[4:6]
            receipt_time = f"{hour}:{minute}:{second}"
        else:
            return {"error": "Invalid time format in verification code"}
    else:
        return {"error": "Verification code does not contain time information"}

    # Set up the session with proper headers
    session = requests.Session()

    # Headers to mimic a real browser request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    session.headers.update(headers)

    try:
        form_url = "https://verify.tra.go.tz/Home/Index"
        form_response = session.get(form_url, timeout=30)
        form_response.raise_for_status()

        form_soup = BeautifulSoup(form_response.text, "html.parser")
        token_input = form_soup.find("input", {"name": "__RequestVerificationToken"})

        if not token_input:
            return {"error": "Could not find verification token in form"}

        verification_token = token_input.get("value")

        form_data = {
            "__RequestVerificationToken": verification_token,
            "RctVcode": verification_code,
        }

        session.headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": form_url,
                "Origin": "https://verify.tra.go.tz",
            }
        )

        response = session.post(
            form_url, data=form_data, timeout=30, allow_redirects=True
        )
        response.raise_for_status()

        if "Please provide your Receipt time" in response.text:

            verification_url = (
                f"https://verify.tra.go.tz/Verify/Verified?Secret={receipt_time}"
            )

            session.headers.update({"Referer": response.url})

            final_response = session.get(verification_url, timeout=30)
            final_response.raise_for_status()

            response = final_response

        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract useful information
        result = {
            "status_code": response.status_code,
            "url": response.url,
            "html_content": response.text,
            "title": soup.title.string if soup.title else None,
            "headers": dict(response.headers),
            "cookies": dict(response.cookies),
            "verification_code_used": verification_code,
            "receipt_time_used": receipt_time,
            "form_token_used": verification_token,
        }

        # Try to extract specific verification data
        verification_data = extract_verification_data(soup)
        result["verification_data"] = verification_data

        # Also store the HTML content for direct parsing
        result["verification_data"]["html_content"] = response.text

        return result

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "status_code": None}


def extract_verification_data(soup):
    """
    Extract specific verification information from the HTML

    Args:
        soup: BeautifulSoup object of the HTML

    Returns:
        dict: Extracted verification data
    """
    data = {}

    # Try to find verification status
    status_elements = soup.find_all(
        ["div", "span", "p"],
        class_=lambda x: x
        and any(
            word in x.lower() for word in ["status", "verified", "valid", "invalid"]
        ),
    )
    if status_elements:
        data["status_elements"] = [
            elem.get_text(strip=True) for elem in status_elements
        ]

    # Look for tables (common in verification systems)
    tables = soup.find_all("table")
    if tables:
        data["tables"] = []
        for table in tables:
            table_data = []
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                row_data = [cell.get_text(strip=True) for cell in cells]
                if row_data:  # Only add non-empty rows
                    table_data.append(row_data)
            if table_data:
                data["tables"].append(table_data)

    # Look for any form inputs (might contain hidden verification data)
    inputs = soup.find_all("input")
    if inputs:
        data["form_inputs"] = []
        for inp in inputs:
            input_data = {
                "name": inp.get("name"),
                "value": inp.get("value"),
                "type": inp.get("type"),
            }
            data["form_inputs"].append(input_data)

    # Extract all text content for analysis
    data["all_text"] = soup.get_text(separator=" ", strip=True)

    return data


def extract_receipt_data(verification_data):
    """
    Extract structured receipt data from verification data

    Args:
        verification_data (dict): Raw verification data from TRA

    Returns:
        dict: Structured receipt data
    """
    receipt_data = {
        "items": [],
        "totals": {},
        "taxes": [],
        "receipt_info": {},
        "company_info": {},
        "customer_info": {},
    }

    if not verification_data:
        return receipt_data

    # If we have HTML content, parse it directly
    html_content = verification_data.get("html_content", "")
    if html_content:
        return extract_receipt_from_html(html_content)

    # Fallback to table-based extraction for backward compatibility
    if "tables" not in verification_data:
        return receipt_data

    # Process tables to extract receipt information
    for table in verification_data["tables"]:
        # Look for items table (usually has Description, Qty, Amount columns)
        if len(table) > 1 and len(table[0]) >= 3:
            header_row = [cell.lower() for cell in table[0]]
            if any(
                word in " ".join(header_row)
                for word in ["description", "qty", "amount", "quantity"]
            ):
                # This looks like an items table
                for row in table[1:]:  # Skip header
                    if len(row) >= 3 and any(cell.strip() for cell in row):
                        item = {
                            "description": row[0].strip() if len(row) > 0 else "",
                            "quantity": row[1].strip() if len(row) > 1 else "",
                            "amount": row[2].strip() if len(row) > 2 else "",
                        }
                        if item["description"]:  # Only add if has description
                            receipt_data["items"].append(item)

        # Look for totals/summary information
        for row in table:
            if len(row) >= 2:
                key = row[0].strip().lower()
                value = row[1].strip() if len(row) > 1 else ""

                # Map common receipt fields
                if "total" in key and "excl" in key:
                    receipt_data["totals"]["subtotal"] = value
                elif "total" in key and "incl" in key:
                    receipt_data["totals"]["grand_total"] = value
                elif "tax" in key and "total" in key:
                    receipt_data["totals"]["total_tax"] = value
                elif "vat" in key:
                    receipt_data["taxes"].append({"type": "VAT", "amount": value})
                elif "receipt" in key and "no" in key:
                    receipt_data["receipt_info"]["receipt_number"] = value
                elif "date" in key:
                    receipt_data["receipt_info"]["date"] = value
                elif "time" in key:
                    receipt_data["receipt_info"]["time"] = value
                elif "tin" in key:
                    receipt_data["company_info"]["tin"] = value
                elif "vrn" in key:
                    receipt_data["company_info"]["vrn"] = value

    return receipt_data


def extract_receipt_from_html(html_content):
    """
    Extract receipt data directly from HTML content using BeautifulSoup

    Args:
        html_content (str): Raw HTML content from TRA verification

    Returns:
        dict: Structured receipt data
    """
    receipt_data = {
        "items": [],
        "totals": {},
        "taxes": [],
        "receipt_info": {},
        "company_info": {},
        "customer_info": {},
        "verification_info": {},
    }

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        extract_company_info(soup, receipt_data)
        extract_customer_info(soup, receipt_data)
        extract_receipt_info(soup, receipt_data)
        extract_items(soup, receipt_data)
        extract_totals_and_taxes(soup, receipt_data)
        extract_verification_info(soup, receipt_data)

    except Exception as e:
        frappe.logger().error(f"Error parsing HTML receipt: {str(e)}")
        receipt_data["parsing_error"] = str(e)

    return receipt_data


def extract_company_info(soup, receipt_data):
    """Extract company information from the receipt HTML"""
    try:
        # Look for company name in the header
        company_header = soup.find("h4")
        if company_header and company_header.find("b"):
            receipt_data["company_info"]["name"] = company_header.find("b").get_text(
                strip=True
            )

        # Extract company details from the invoice-info section
        invoice_info = soup.find("div", class_="invoice-info")
        if invoice_info:
            text_content = invoice_info.get_text()

            # Extract TIN
            if "TIN:" in text_content:
                tin_match = text_content.split("TIN:")[1].split("\n")[0].strip()
                receipt_data["company_info"]["tin"] = tin_match

            # Extract VRN
            if "VRN:" in text_content:
                vrn_match = text_content.split("VRN:")[1].split("\n")[0].strip()
                receipt_data["company_info"]["vrn"] = vrn_match

            # Extract Serial Number
            if "SERIAL NO:" in text_content:
                serial_match = (
                    text_content.split("SERIAL NO:")[1].split("\n")[0].strip()
                )
                receipt_data["company_info"]["serial_number"] = serial_match

            # Extract UIN
            if "UIN:" in text_content:
                uin_match = text_content.split("UIN:")[1].split("\n")[0].strip()
                receipt_data["company_info"]["uin"] = uin_match

            # Extract Tax Office
            if "TAX OFFICE:" in text_content:
                tax_office_match = (
                    text_content.split("TAX OFFICE:")[1].split("\n")[0].strip()
                )
                receipt_data["company_info"]["tax_office"] = tax_office_match

            # Extract Mobile
            if "MOBILE:" in text_content:
                mobile_match = text_content.split("MOBILE:")[1].split("\n")[0].strip()
                receipt_data["company_info"]["mobile"] = mobile_match

            # Extract Address (P.O.BOX)
            if "P.O.BOX" in text_content:
                address_match = text_content.split("P.O.BOX")[1].split("\n")[0].strip()
                receipt_data["company_info"]["address"] = f"P.O.BOX{address_match}"

    except Exception as e:
        frappe.logger().error(f"Error extracting company info: {str(e)}")


def extract_customer_info(soup, receipt_data):
    """Extract customer information from the receipt HTML"""
    try:
        # Find all invoice-header divs and look for customer information
        invoice_headers = soup.find_all("div", class_="invoice-header")

        for header in invoice_headers:
            text_content = header.get_text()

            # Extract Customer Name
            if "CUSTOMER NAME:" in text_content:
                customer_name = (
                    text_content.split("CUSTOMER NAME:")[1].split("\n")[0].strip()
                )
                receipt_data["customer_info"]["name"] = customer_name

            # Extract Customer ID Type
            if "CUSTOMER ID TYPE:" in text_content:
                id_type = (
                    text_content.split("CUSTOMER ID TYPE:")[1].split("\n")[0].strip()
                )
                receipt_data["customer_info"]["id_type"] = id_type

            # Extract Customer ID
            if "CUSTOMER ID:" in text_content:
                customer_id = (
                    text_content.split("CUSTOMER ID:")[1].split("\n")[0].strip()
                )
                receipt_data["customer_info"]["id"] = customer_id

            # Extract Customer Mobile
            if "CUSTOMER MOBILE:" in text_content:
                mobile = (
                    text_content.split("CUSTOMER MOBILE:")[1].split("\n")[0].strip()
                )
                receipt_data["customer_info"]["mobile"] = mobile

    except Exception as e:
        frappe.logger().error(f"Error extracting customer info: {str(e)}")


def extract_receipt_info(soup, receipt_data):
    """Extract receipt information from the receipt HTML"""
    try:
        # Find all invoice-header divs and look for receipt information
        invoice_headers = soup.find_all("div", class_="invoice-header")

        for header in invoice_headers:
            text_content = header.get_text()

            # Extract Receipt Number
            if "RECEIPT NO:" in text_content:
                receipt_no = text_content.split("RECEIPT NO:")[1].split("\n")[0].strip()
                receipt_data["receipt_info"]["receipt_number"] = receipt_no

            # Extract Z Number
            if "Z NUMBER:" in text_content:
                z_number = text_content.split("Z NUMBER:")[1].split("\n")[0].strip()
                receipt_data["receipt_info"]["z_number"] = z_number

            # Extract Receipt Date
            if "RECEIPT DATE:" in text_content:
                receipt_date = (
                    text_content.split("RECEIPT DATE:")[1].split("\n")[0].strip()
                )
                receipt_data["receipt_info"]["date"] = receipt_date

            # Extract Receipt Time
            if "RECEIPT TIME:" in text_content:
                receipt_time = (
                    text_content.split("RECEIPT TIME:")[1].split("\n")[0].strip()
                )
                receipt_data["receipt_info"]["time"] = receipt_time

    except Exception as e:
        frappe.logger().error(f"Error extracting receipt info: {str(e)}")


def extract_items(soup, receipt_data):
    """Extract purchased items from the receipt HTML"""
    try:
        # Find the items table
        items_table = soup.find("table", class_="table-striped")
        if items_table:
            tbody = items_table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        item = {
                            "description": cells[0].get_text(strip=True),
                            "quantity": cells[1].get_text(strip=True),
                            "amount": cells[2].get_text(strip=True),
                        }
                        if item["description"]:  # Only add if has description
                            receipt_data["items"].append(item)

    except Exception as e:
        frappe.logger().error(f"Error extracting items: {str(e)}")


def extract_totals_and_taxes(soup, receipt_data):
    """Extract totals and tax information from the receipt HTML"""
    try:
        # Find the totals table (the one without table-striped class)
        tables = soup.find_all("table", class_="table")

        for table in tables:
            if "table-striped" not in table.get("class", []):
                tbody = table.find("tbody")
                if tbody:
                    rows = tbody.find_all("tr")
                    for row in rows:
                        cells = row.find_all(["th", "td"])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).upper()
                            value = cells[1].get_text(strip=True)

                            # Map the totals
                            if "TOTAL EXCL OF TAX" in label:
                                receipt_data["totals"]["subtotal"] = value
                            elif "TOTAL INCL OF TAX" in label:
                                receipt_data["totals"]["grand_total"] = value
                            elif "TOTAL TAX" in label:
                                receipt_data["totals"]["total_tax"] = value
                            elif "TAX RATE" in label:
                                # Extract tax rate and amount
                                tax_info = {
                                    "label": label,
                                    "amount": value,
                                }
                                # Extract rate percentage if available
                                if "(" in label and "%" in label:
                                    rate_part = label.split("(")[1].split(")")[0]
                                    tax_info["rate"] = rate_part
                                receipt_data["taxes"].append(tax_info)

    except Exception as e:
        frappe.logger().error(f"Error extracting totals and taxes: {str(e)}")


def extract_verification_info(soup, receipt_data):
    """Extract verification information from the receipt HTML"""
    try:
        # Look for verification code
        verification_headers = soup.find_all("h4")
        for header in verification_headers:
            text = header.get_text(strip=True)
            if "RECEIPT VERIFICATION CODE" in text:
                # The next h4 should contain the actual code
                next_h4 = header.find_next("h4")
                if next_h4:
                    verification_code = next_h4.get_text(strip=True)
                    receipt_data["verification_info"]["code"] = verification_code

        # Look for QR code image
        qr_img = soup.find("img", {"id": "barcode"})
        if qr_img:
            qr_src = qr_img.get("src", "")
            qr_title = qr_img.get("title", "")
            receipt_data["verification_info"]["qr_code_url"] = qr_src
            receipt_data["verification_info"]["qr_code_data"] = qr_title

            # Extract verification URL from QR code data parameter
            if "data=" in qr_src:
                verification_url = qr_src.split("data=")[1].split("&")[0]
                receipt_data["verification_info"]["verification_url"] = verification_url

    except Exception as e:
        frappe.logger().error(f"Error extracting verification info: {str(e)}")


def create_tra_tax_inv_document(verification_code, receipt_data, verification_result):
    """
    Create a TRA Tax Inv document from successful verification data

    Args:
        verification_code (str): The verification code used
        receipt_data (dict): Extracted receipt data
        verification_result (dict): Full verification result

    Returns:
        dict: Result of document creation
    """
    try:
        # Check if document already exists
        existing = frappe.db.exists(
            "TRA TAX Inv", {"verification_code": verification_code}
        )
        if existing:
            frappe.logger().info(
                f"TRA TAX Inv already exists for verification code: {verification_code}"
            )
            return {
                "success": False,
                "message": f"TRA TAX Inv already exists for verification code: {verification_code}",
                "existing_doc": existing,
            }

        # Create new TRA TAX Inv document
        doc = frappe.new_doc("TRA TAX Inv")
        doc.verification_code = verification_code
        doc.type = "Sales"  # Default to Sales, can be changed later
        doc.verification_status = "Verified"
        doc.verification_url = str(verification_result.get("url", ""))

        # Populate basic information
        company_info = receipt_data.get("company_info", {})
        doc.company_name = company_info.get("name", "")

        receipt_info = receipt_data.get("receipt_info", {})
        doc.receipt_number = receipt_info.get("receipt_number", "")

        # Populate totals
        totals = receipt_data.get("totals", {})
        if totals.get("subtotal"):
            try:
                subtotal_str = str(totals.get("subtotal", "0")).replace(",", "")
                doc.subtotal = float(subtotal_str)
            except:
                pass

        if totals.get("total_tax"):
            try:
                total_tax_str = str(totals.get("total_tax", "0")).replace(",", "")
                doc.total_tax = float(total_tax_str)
            except:
                pass

        if totals.get("grand_total"):
            try:
                grand_total_str = str(totals.get("grand_total", "0")).replace(",", "")
                doc.grand_total = float(grand_total_str)
            except:
                pass

        # Populate items
        items = receipt_data.get("items", [])
        for item in items:
            item_row = doc.append("items", {})
            item_row.description = item.get("description", "")
            item_row.quantity = item.get("quantity", "")
            if item.get("amount"):
                try:
                    amount_str = str(item.get("amount", "0")).replace(",", "")
                    item_row.amount = float(amount_str)
                except:
                    item_row.amount = 0

        # Save the document
        doc.insert()

        frappe.logger().info(
            f"TRA TAX Inv created successfully: {doc.name} for verification code: {verification_code}"
        )

        return {
            "success": True,
            "message": "TRA TAX Inv created successfully",
            "doc_name": doc.name,
            "verification_status": doc.verification_status,
        }

    except Exception as e:
        frappe.logger().error(
            f"Error creating TRA TAX Inv for verification code {verification_code}: {str(e)}"
        )
        return {"success": False, "message": f"Error creating TRA TAX Inv: {str(e)}"}
