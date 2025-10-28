# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, formatdate, flt, get_datetime
from frappe.utils.dashboard import cache_source
from erpnext.accounts.utils import get_balance_on
from datetime import datetime, timedelta
import json

@frappe.whitelist()
def get(chart_name=None, chart=None, no_cache=None, filters=None, from_date=None, to_date=None, timespan=None, time_interval=None, heatmap_year=None):
    """
    Main entry point for Multi_Account Balance Timeline dashboard chart source
    This function is called by Frappe's dashboard framework via CSF_TZ module
    """
    multi_balance = MultiBankBalance()
    return multi_balance.get(chart_name, chart, no_cache, filters, from_date, to_date)

@frappe.whitelist()
def get_sample_data(chart_name=None, **kwargs):
    """
    Generate sample data for testing when no real transactions exist
    This helps users see how the chart would look with data
    """
    try:
        multi_balance = MultiBankBalance()
        return multi_balance.get_sample_data(**kwargs)
    except Exception as e:
        frappe.log_error(f"get_sample_data failed: {str(e)}", "Sample Data Error")
        # Return minimal working sample data
        return {
            'labels': ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
            'datasets': [
                {
                    'name': 'Sample Account',
                    'values': [1000, 1200, 1100, 1300, 1250],
                    'chartType': 'line',
                    'color': '#1f77b4'
                }
            ],
            'type': 'line',
            'is_sample_data': True,
            'sample_message': 'This is minimal sample data for demonstration.',
            'summary': {
                'total_balance': 1250,
                'account_count': 1,
                'highest_balance_account': 'Sample Account',
                'highest_balance': 1250,
                'as_of_date': frappe.utils.formatdate(frappe.utils.today())
            }
        }

@frappe.whitelist()
def create_sample_accounts(company):
    """
    Create sample bank accounts for testing purposes

    Args:
        company (str): Company name to create accounts for

    Returns:
        list: Created account names
    """
    multi_balance = MultiBankBalance()
    return multi_balance.create_sample_accounts(company)

@frappe.whitelist()
def debug_chart_data(company=None):
    """
    Debug function to test chart data generation step by step
    """
    try:
        if not company:
            company = frappe.defaults.get_global_default("company") or "Test Company"

        multi_balance = MultiBankBalance()

        # Test step by step
        result = {
            "step": "starting",
            "company": company,
            "error": None
        }

        # Step 1: Test filter validation
        try:
            filters = multi_balance.validate_and_process_filters({"company": company})
            result["step"] = "filters_validated"
            result["filters"] = filters
        except Exception as e:
            result["error"] = f"Filter validation failed: {str(e)}"
            return result

        # Step 2: Test date validation
        try:
            from_date, to_date = multi_balance.validate_date_range(None, None)
            result["step"] = "dates_validated"
            result["from_date"] = str(from_date)
            result["to_date"] = str(to_date)
        except Exception as e:
            result["error"] = f"Date validation failed: {str(e)}"
            return result

        # Step 3: Test account retrieval
        try:
            accounts = multi_balance.get_bank_accounts(company, "Bank")
            result["step"] = "accounts_retrieved"
            result["account_count"] = len(accounts) if accounts else 0
            result["accounts"] = [acc.get('name', 'Unknown') for acc in (accounts or [])]
        except Exception as e:
            result["error"] = f"Account retrieval failed: {str(e)}"
            return result

        # Step 4: Test sample data generation
        try:
            sample_data = multi_balance.get_sample_data(company=company)
            result["step"] = "sample_data_generated"
            result["sample_data_keys"] = list(sample_data.keys())
            result["dataset_count"] = len(sample_data.get('datasets', []))
        except Exception as e:
            result["error"] = f"Sample data generation failed: {str(e)}"
            return result

        result["step"] = "completed_successfully"
        return result

    except Exception as e:
        return {
            "step": "failed",
            "error": f"Debug function failed: {str(e)}",
            "company": company
        }

class MultiBankBalance:
    """
    Custom dashboard chart source for displaying multiple bank account balances
    Extends the functionality of the standard Account Balance Timeline
    """
    
    def get(self, chart_name=None, chart=None, no_cache=None, filters=None, from_date=None, to_date=None):
        """
        Main entry point called by Frappe dashboard framework via CSF_TZ module

        Args:
            chart_name (str): Name of the dashboard chart
            chart (dict): Chart configuration object
            no_cache (bool): Whether to bypass cache
            filters (dict): Chart filters including company, account_type, etc.
            from_date (str): Start date for data retrieval
            to_date (str): End date for data retrieval

        Returns:
            dict: Formatted chart data with labels and datasets
        """
        try:
            # Parse filters if they come as JSON string
            if isinstance(filters, str):
                import json
                try:
                    filters = json.loads(filters)
                except (json.JSONDecodeError, TypeError):
                    filters = {}

            # Validate and process inputs
            filters = self.validate_and_process_filters(filters)
            from_date, to_date = self.validate_date_range(from_date, to_date)
            
            # Get bank accounts for the company
            accounts = self.get_bank_accounts(
                company=filters.get('company'),
                account_type=filters.get('account_type', 'Bank'),
                include_inactive=filters.get('include_inactive', False),
                currency=filters.get('currency')
            )

            # If no accounts found, return empty chart with helpful message
            if not accounts or len(accounts) == 0:
                return self.empty_chart_data(_("No bank accounts found for the selected criteria. Please create bank accounts first."))

            # Get balance data for all accounts
            balance_data = self.get_account_balances(accounts, from_date, to_date)

            # Format data for chart display
            chart_data = self.format_chart_data(balance_data, accounts, from_date, to_date)

            # Check if we have any real data
            has_real_data = False
            if balance_data:
                for date_data in balance_data.values():
                    if any(balance != 0 for balance in date_data.values()):
                        has_real_data = True
                        break

            # If we have accounts but no real transaction data, add helpful message
            if not has_real_data:
                chart_data['no_data_message'] = _(
                    "Found {0} bank account(s) but no transaction data in the selected date range. "
                    "Create some transactions to see balance trends."
                ).format(len(accounts))
                chart_data['empty'] = True

            return chart_data
            
        except Exception as e:
            import traceback
            error_msg = f"Error in MultiBankBalance.get: {str(e)}\n{traceback.format_exc()}"
            frappe.log_error(error_msg, "Multi_Account Balance Timeline Error")

            # Return empty chart with error message
            return self.empty_chart_data(_("Error retrieving bank balance data. Please check the error logs for details."))
    
    def validate_and_process_filters(self, filters):
        """
        Validate and process chart filters
        
        Args:
            filters (dict): Raw filters from chart
            
        Returns:
            dict: Processed and validated filters
        """
        if not filters:
            filters = {}
        
        # Company is required
        if not filters.get('company'):
            frappe.throw(_("Company filter is required for Multi_Bank Balance chart"))
        
        # Validate company exists and user has access
        if not frappe.db.exists('Company', filters.get('company')):
            frappe.throw(_("Invalid company: {0}").format(filters.get('company')))
        
        # Set default account type if not provided
        if not filters.get('account_type'):
            filters['account_type'] = 'Bank'
        
        # Validate account type
        valid_account_types = ['Bank', 'Cash']
        if filters.get('account_type') not in valid_account_types:
            filters['account_type'] = 'Bank'
        
        return filters
    
    def validate_date_range(self, from_date, to_date):
        """
        Validate and set default date range
        
        Args:
            from_date (str): Start date
            to_date (str): End date
            
        Returns:
            tuple: (from_date, to_date) as date objects
        """
        if not from_date:
            from_date = add_days(frappe.utils.today(), -365)  # Default to 1 year ago
        
        if not to_date:
            to_date = frappe.utils.today()
        
        from_date = getdate(from_date)
        to_date = getdate(to_date)
        
        # Ensure from_date is not after to_date
        if from_date > to_date:
            frappe.throw(_("From Date cannot be after To Date"))
        
        # Limit the date range to prevent performance issues
        max_days = 1095  # 3 years
        if (to_date - from_date).days > max_days:
            frappe.throw(_("Date range cannot exceed {0} days").format(max_days))
        
        return from_date, to_date
    
    def get_bank_accounts(self, company, account_type="Bank", include_inactive=False, currency=None):
        """
        Retrieve all bank accounts for the specified company
        
        Args:
            company (str): Company name
            account_type (str): Type of accounts to retrieve (Bank/Cash)
            include_inactive (bool): Whether to include disabled accounts
            currency (str): Filter by currency (optional)
            
        Returns:
            list: List of account dictionaries
        """
        conditions = []
        values = [company, account_type]
        
        # Base query
        query = """
            SELECT 
                name,
                account_name,
                account_type,
                account_currency,
                parent_account,
                root_type,
                is_group,
                disabled
            FROM `tabAccount`
            WHERE company = %s
                AND account_type = %s
                AND is_group = 0
        """
        
        # Add conditions based on parameters
        if not include_inactive:
            query += " AND disabled = 0"
        
        if currency:
            query += " AND account_currency = %s"
            values.append(currency)
        
        query += " ORDER BY account_name"
        
        accounts = frappe.db.sql(query, values, as_dict=True)
        
        # Filter accounts based on user permissions
        allowed_accounts = []
        for account in accounts:
            if self.has_account_permission(account.name):
                allowed_accounts.append(account)
        
        return allowed_accounts
    
    def has_account_permission(self, account):
        """
        Check if current user has permission to view the account
        
        Args:
            account (str): Account name
            
        Returns:
            bool: True if user has permission
        """
        try:
            # Use ERPNext's permission system
            return frappe.has_permission('Account', 'read', account)
        except:
            # Default to True if permission check fails
            return True
    
    def get_account_balances(self, accounts, from_date, to_date):
        """
        Calculate balances for multiple accounts over time period
        
        Args:
            accounts (list): List of account dictionaries
            from_date (date): Start date
            to_date (date): End date
            
        Returns:
            dict: Account balances organized by date and account
        """
        if not accounts:
            return {}
        
        account_names = [acc['name'] for acc in accounts]
        
        # Get all GL entries for these accounts in the date range
        gl_entries = frappe.db.sql("""
            SELECT 
                account,
                posting_date,
                SUM(debit - credit) as net_amount
            FROM `tabGL Entry`
            WHERE account IN ({0})
                AND posting_date BETWEEN %s AND %s
                AND is_cancelled = 0
            GROUP BY account, posting_date
            ORDER BY posting_date, account
        """.format(','.join(['%s'] * len(account_names))), 
        account_names + [from_date, to_date], as_dict=True)
        
        # Build running balances
        balance_data = {}
        account_running_balances = {}
        
        # Initialize running balances with opening balances
        for account in accounts:
            opening_balance = get_balance_on(account['name'], from_date)
            account_running_balances[account['name']] = flt(opening_balance)
        
        # Generate date range
        date_range = self.get_date_range(from_date, to_date)
        
        # Initialize balance data structure
        for date in date_range:
            balance_data[date] = {}
            for account in accounts:
                balance_data[date][account['name']] = account_running_balances[account['name']]
        
        # Process GL entries and update running balances
        current_date = from_date
        for entry in gl_entries:
            entry_date = entry['posting_date']
            account = entry['account']
            
            # Update running balance for this account
            if account in account_running_balances:
                account_running_balances[account] += flt(entry['net_amount'])
                
                # Update all dates from this entry date onwards
                for date in date_range:
                    if date >= entry_date:
                        balance_data[date][account] = account_running_balances[account]
        
        return balance_data
    
    def get_date_range(self, from_date, to_date, interval='daily'):
        """
        Generate list of dates between from_date and to_date
        
        Args:
            from_date (date): Start date
            to_date (date): End date
            interval (str): Date interval (daily, weekly, monthly)
            
        Returns:
            list: List of dates
        """
        dates = []
        current_date = from_date
        
        if interval == 'daily':
            while current_date <= to_date:
                dates.append(current_date)
                current_date = add_days(current_date, 1)
        elif interval == 'weekly':
            while current_date <= to_date:
                dates.append(current_date)
                current_date = add_days(current_date, 7)
        elif interval == 'monthly':
            while current_date <= to_date:
                dates.append(current_date)
                # Add one month (approximate)
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        
        # Ensure to_date is included if not already
        if dates and dates[-1] != to_date:
            dates.append(to_date)
        
        return dates
    
    def format_chart_data(self, balance_data, accounts, from_date, to_date):
        """
        Format balance data for chart consumption

        Args:
            balance_data (dict): Raw balance data by date and account
            accounts (list): List of account dictionaries
            from_date (date): Start date
            to_date (date): End date

        Returns:
            dict: Formatted chart data
        """
        if not balance_data or not accounts:
            return self.empty_chart_data(_("No data available"))

        # Prepare labels (dates)
        labels = []
        dates = sorted(balance_data.keys())

        # Ensure we have valid dates
        if not dates:
            return self.empty_chart_data(_("No date data available"))

        for date in dates:
            labels.append(formatdate(date, "MMM d"))

        # Prepare datasets (one per account)
        datasets = []
        colors = self.get_chart_colors(len(accounts))

        for idx, account in enumerate(accounts):
            account_name = account['name']
            account_label = account['account_name'] or account_name

            # Ensure account_label is not empty
            if not account_label or account_label.strip() == '':
                account_label = f"Account {idx + 1}"

            # Get balance values for this account
            values = []
            for date in dates:
                balance = balance_data.get(date, {}).get(account_name, 0)
                # Ensure balance is a valid number
                balance_value = flt(balance, 2)
                values.append(balance_value)

            # Ensure we have valid color
            color = colors[idx % len(colors)]
            if not color or color.strip() == '':
                color = '#1f77b4'  # Default blue color

            # Create dataset for this account
            dataset = {
                'name': str(account_label),  # Ensure string
                'values': values,
                'chartType': 'line',
                'color': color
            }
            datasets.append(dataset)

        # Ensure we have at least one dataset
        if not datasets:
            return self.empty_chart_data(_("No account data available"))

        # Calculate summary statistics
        summary = self.calculate_summary_stats(balance_data, accounts)

        chart_data = {
            'labels': labels,
            'datasets': datasets,
            'type': 'line',
            'summary': summary,
            'account_count': len(accounts)
        }

        return chart_data

    def get_sample_data(self, **kwargs):
        """
        Generate sample data for testing and demonstration purposes

        Args:
            **kwargs: Optional parameters (company, account_type, etc.)

        Returns:
            dict: Sample chart data with realistic-looking balance trends
        """
        import random
        from datetime import datetime, timedelta

        # Create sample accounts
        sample_accounts = [
            {'name': 'Sample Bank Account 1', 'account_name': 'Main Checking Account'},
            {'name': 'Sample Bank Account 2', 'account_name': 'Business Savings Account'},
            {'name': 'Sample Bank Account 3', 'account_name': 'Petty Cash Account'},
        ]

        # Generate date range (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        # Generate sample balance data
        sample_balance_data = {}
        current_date = start_date

        # Starting balances for each account
        account_balances = {
            'Sample Bank Account 1': 50000.00,  # Main checking starts high
            'Sample Bank Account 2': 25000.00,  # Savings moderate
            'Sample Bank Account 3': 2000.00,   # Petty cash low
        }

        while current_date <= end_date:
            daily_balances = {}

            for account in sample_accounts:
                account_name = account['name']
                current_balance = account_balances[account_name]

                # Simulate realistic daily changes
                if account_name == 'Sample Bank Account 1':  # Main checking - more volatile
                    change = random.uniform(-2000, 3000)
                elif account_name == 'Sample Bank Account 2':  # Savings - stable growth
                    change = random.uniform(-100, 200)
                else:  # Petty cash - small changes
                    change = random.uniform(-50, 100)

                # Apply change and ensure minimum balance
                new_balance = max(0, current_balance + change)
                account_balances[account_name] = new_balance
                daily_balances[account_name] = new_balance

            sample_balance_data[current_date] = daily_balances
            current_date += timedelta(days=1)

        # Format the sample data using existing formatting method
        chart_data = self.format_chart_data(sample_balance_data, sample_accounts, start_date, end_date)

        # Add sample data indicator
        chart_data['is_sample_data'] = True
        chart_data['sample_message'] = _("This is sample data for demonstration. Create bank accounts and transactions to see real data.")

        return chart_data

    @frappe.whitelist()
    def create_sample_accounts(self, company):
        """
        Create sample bank accounts for testing purposes

        Args:
            company (str): Company name to create accounts for

        Returns:
            list: Created account names
        """
        if not frappe.has_permission("Account", "create"):
            frappe.throw(_("You don't have permission to create accounts"))

        # Check if company exists
        if not frappe.db.exists("Company", company):
            frappe.throw(_("Company {0} does not exist").format(company))

        # Get company's chart of accounts root
        company_doc = frappe.get_doc("Company", company)

        # Find or create Bank Accounts group
        bank_accounts_group = None
        try:
            bank_accounts_group = frappe.db.get_value("Account", {
                "company": company,
                "account_name": "Bank Accounts",
                "is_group": 1
            })
        except:
            pass

        if not bank_accounts_group:
            # Create Bank Accounts group under Assets
            assets_account = frappe.db.get_value("Account", {
                "company": company,
                "account_name": "Assets",
                "is_group": 1
            })

            if assets_account:
                bank_group = frappe.get_doc({
                    "doctype": "Account",
                    "account_name": "Bank Accounts",
                    "parent_account": assets_account,
                    "company": company,
                    "is_group": 1,
                    "account_type": "Bank"
                })
                bank_group.insert()
                bank_accounts_group = bank_group.name

        # Sample accounts to create
        sample_accounts = [
            {
                "account_name": "Sample Checking Account",
                "account_type": "Bank"
            },
            {
                "account_name": "Sample Savings Account",
                "account_type": "Bank"
            },
            {
                "account_name": "Sample Cash Account",
                "account_type": "Cash"
            }
        ]

        created_accounts = []

        for account_info in sample_accounts:
            account_name = f"{account_info['account_name']} - {company}"

            # Check if account already exists
            if frappe.db.exists("Account", account_name):
                continue

            try:
                account = frappe.get_doc({
                    "doctype": "Account",
                    "account_name": account_info['account_name'],
                    "parent_account": bank_accounts_group,
                    "company": company,
                    "is_group": 0,
                    "account_type": account_info['account_type'],
                    "account_currency": company_doc.default_currency
                })
                account.insert()
                created_accounts.append(account.name)

            except Exception as e:
                frappe.log_error(f"Failed to create sample account {account_info['account_name']}: {str(e)}")

        if created_accounts:
            frappe.msgprint(
                _("Created {0} sample accounts: {1}").format(
                    len(created_accounts),
                    ", ".join([acc.split(" - ")[0] for acc in created_accounts])
                ),
                title=_("Sample Accounts Created"),
                indicator="green"
            )

        return created_accounts

    def calculate_summary_stats(self, balance_data, accounts):
        """
        Calculate summary statistics for the chart
        
        Args:
            balance_data (dict): Balance data
            accounts (list): Account list
            
        Returns:
            dict: Summary statistics
        """
        if not balance_data:
            return {}
        
        dates = sorted(balance_data.keys())
        latest_date = dates[-1] if dates else None
        
        if not latest_date:
            return {}
        
        latest_balances = balance_data.get(latest_date, {})
        total_balance = sum(flt(balance) for balance in latest_balances.values())
        
        # Find account with highest balance
        max_balance = 0
        max_account = ""
        for account in accounts:
            balance = latest_balances.get(account['name'], 0)
            if balance > max_balance:
                max_balance = balance
                max_account = account['account_name'] or account['name']
        
        return {
            'total_balance': flt(total_balance, 2),
            'account_count': len(accounts),
            'highest_balance_account': max_account,
            'highest_balance': flt(max_balance, 2),
            'as_of_date': formatdate(latest_date)
        }
    
    def get_chart_colors(self, count):
        """
        Get color palette for chart lines

        Args:
            count (int): Number of colors needed

        Returns:
            list: List of color codes
        """
        # Ensure count is valid
        if not count or count <= 0:
            count = 1

        base_colors = [
            '#1f77b4',  # Blue
            '#ff7f0e',  # Orange
            '#2ca02c',  # Green
            '#d62728',  # Red
            '#9467bd',  # Purple
            '#8c564b',  # Brown
            '#e377c2',  # Pink
            '#7f7f7f',  # Gray
            '#bcbd22',  # Olive
            '#17becf',  # Cyan
        ]

        # Ensure we have valid base colors
        if not base_colors:
            base_colors = ['#1f77b4']  # Fallback to blue

        # Extend colors if more are needed
        colors = []
        for i in range(count):
            color = base_colors[i % len(base_colors)]
            # Ensure color is valid
            if not color or not isinstance(color, str) or color.strip() == '':
                color = '#1f77b4'  # Default blue
            colors.append(color)

        return colors
    
    def empty_chart_data(self, message):
        """
        Return empty chart data with message

        Args:
            message (str): Message to display

        Returns:
            dict: Empty chart data structure
        """
        # Ensure message is a string
        if not message or not isinstance(message, str):
            message = "No data available"

        return {
            'labels': [],
            'datasets': [],
            'type': 'line',
            'message': str(message),
            'empty': True,
            'summary': {
                'total_balance': 0,
                'account_count': 0,
                'highest_balance_account': '',
                'highest_balance': 0,
                'as_of_date': formatdate(frappe.utils.today())
            }
        }

# Additional utility functions for the Multi_Bank Balance source

def get_default_bank_account(company):
    """
    Get the default bank account for a company
    
    Args:
        company (str): Company name
        
    Returns:
        str: Default bank account name
    """
    return frappe.db.get_value('Company', company, 'default_bank_account')

def validate_chart_permissions(chart_name):
    """
    Validate if user has permission to view the chart
    
    Args:
        chart_name (str): Chart name
        
    Returns:
        bool: Permission status
    """
    return frappe.has_permission('Dashboard Chart', 'read', chart_name)

def get_account_currencies(company):
    """
    Get all currencies used in bank accounts for a company

    Args:
        company (str): Company name

    Returns:
        list: List of currencies
    """
    return frappe.db.sql("""
        SELECT DISTINCT account_currency
        FROM `tabAccount`
        WHERE company = %s
        AND account_type IN ('Bank', 'Cash')
        AND account_currency IS NOT NULL
        ORDER BY account_currency
    """, company, pluck=True)

@frappe.whitelist()
def create_test_transactions(company, account_name=None, amount=10000):
    """
    Create test transactions for a bank account to generate chart data

    Args:
        company (str): Company name
        account_name (str): Specific account name (optional)
        amount (float): Transaction amount (default: 10000)

    Returns:
        dict: Result with created transactions
    """
    if not frappe.has_permission("Journal Entry", "create"):
        frappe.throw(_("You don't have permission to create Journal Entries"))

    # Get bank accounts
    if account_name:
        accounts = [{"name": account_name}]
    else:
        accounts = frappe.db.get_all("Account",
            filters={
                "company": company,
                "account_type": ["in", ["Bank", "Cash"]],
                "is_group": 0,
                "disabled": 0
            },
            fields=["name", "account_name"],
            limit=3  # Limit to first 3 accounts
        )

    if not accounts:
        frappe.throw(_("No bank accounts found for company {0}").format(company))

    # Get a cash account for balancing entries
    cash_account = frappe.db.get_value("Account", {
        "company": company,
        "account_type": "Cash",
        "is_group": 0,
        "disabled": 0
    })

    if not cash_account:
        # Try to find any asset account for balancing
        cash_account = frappe.db.get_value("Account", {
            "company": company,
            "root_type": "Asset",
            "is_group": 0,
            "disabled": 0
        })

    if not cash_account:
        frappe.throw(_("No cash or asset account found for balancing entries"))

    created_entries = []

    # Create test transactions for each account
    for account in accounts:
        try:
            # Create a deposit transaction
            je = frappe.get_doc({
                "doctype": "Journal Entry",
                "company": company,
                "posting_date": frappe.utils.add_days(frappe.utils.today(), -30),
                "entry_type": "Bank Entry",
                "accounts": [
                    {
                        "account": account["name"],
                        "debit_in_account_currency": float(amount),
                        "credit_in_account_currency": 0
                    },
                    {
                        "account": cash_account,
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": float(amount)
                    }
                ]
            })
            je.insert()
            je.submit()
            created_entries.append({
                "journal_entry": je.name,
                "account": account["name"],
                "amount": amount,
                "type": "deposit"
            })

            # Create a withdrawal transaction
            je2 = frappe.get_doc({
                "doctype": "Journal Entry",
                "company": company,
                "posting_date": frappe.utils.add_days(frappe.utils.today(), -15),
                "entry_type": "Bank Entry",
                "accounts": [
                    {
                        "account": account["name"],
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": float(amount) * 0.3  # 30% withdrawal
                    },
                    {
                        "account": cash_account,
                        "debit_in_account_currency": float(amount) * 0.3,
                        "credit_in_account_currency": 0
                    }
                ]
            })
            je2.insert()
            je2.submit()
            created_entries.append({
                "journal_entry": je2.name,
                "account": account["name"],
                "amount": float(amount) * 0.3,
                "type": "withdrawal"
            })

        except Exception as e:
            frappe.log_error(f"Failed to create test transaction for {account['name']}: {str(e)}")

    if created_entries:
        frappe.msgprint(
            _("Created {0} test transactions. You can now view the Multi_Account Balance Timeline chart with real data.").format(len(created_entries)),
            title=_("Test Transactions Created"),
            indicator="green"
        )

    return {
        "success": True,
        "created_entries": created_entries,
        "message": f"Created {len(created_entries)} test transactions"
    }