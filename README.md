# CSF TZ



Welcome to the **Country Specific Functionality Tanzania** repository. This project enhances ERPNext with country-specific functionality tailored for businesses operating in Tanzania, ensuring compliance with local regulations and optimising business processes.

## **Overview**

This repository contains the customizations and configurations necessary to adapt ERPNext to meet the specific needs of Tanzanian businesses. By leveraging the powerful capabilities of ERPNext and the flexibility of the Frappe Framework, this solution provides robust support for Tanzanian tax compliance, localised accounting, inventory management, payroll, and more.

## **Features**

### **Tanzanian Tax Compliance**

* **Electronic Fiscal Devices (EFDs) Integration** \- Seamlessly integrate with EFDs and generate EFD Z Reports to comply with Tanzania Revenue Authority (TRA) regulations.  
* **Automated Tax Calculations** \- Configure automated VAT and tax calculations to ensure all transactions are compliant with Tanzanian tax laws.

### **Localised Accounting and Financial Management**

* **Bank Charges and Reconciliation** \- Automate the management of bank charges with the CSF TZ Bank Charges feature and streamline reconciliations with Tanzanian banks.  
* **Currency Management** \- Efficiently handle transactions in multiple currencies, specifically tailored for the Tanzanian Shilling (TZS).

### **Enhanced Inventory and Stock Management**

* **Stock Management Tools** \- Utilise the Item Barcode Update Tool and Dynamic Price List Assignment for precise inventory control.  
* **Inter-Company Stock Transfers** \- Simplify stock movements between branches or entities with the Inter Company Stock Transfer feature.

### **Comprehensive Payroll and HR Management**

* **Employee Data and Payroll** \- Manage payroll, employee data changes, and salary slip distribution with features like Employee Data Change Request and Email Salary Slips.  
* **Piecework and Salary Disbursement** \- Customise payroll processes to include piecework payments and diverse salary components, enhancing labour management.

### **Document and Record Management**

* **Secure Document Handling** \- Manage document attachments securely with Attachment Type and File Attachment features, ensuring safe storage and retrieval.  
* **Visitor and Vehicle Management** \- Efficiently track visitors and manage vehicle-related activities with Visitors Registration Card, Vehicle Fine Record, and Vehicle Service Log.

### **Localised Data and Settings**

* **Tanzanian Geographic Data** \- Accurately configure the ERP system with Tanzanian regions, districts, wards, villages, and postal codes for precise local information.  
* **Compliance and Regulatory Features** \- Implement Selcom Integration for streamlined payment processing and manage parking bills and fines with localised settings.

### **Project and Maintenance Management**

* **Project Tracking** \- Manage projects with tools like Mokasi Project, Mokasi Equipment Name, and Mokasi Activity, ideal for project-based businesses.  
* **Maintenance Services** \- Track and manage maintenance requests and services with Maintenance Request and Maintenance Services Table.

### **Automated Reporting and Logs**

* **Scheduled Reports** \- Automate regular reports with Scheduled Auto Email Report for timely decision-making.  
* **Operational Logs** \- Maintain comprehensive logs of critical business activities with QR Code Log and CSF API Response Log.

## **Installation**

To install this application, please follow these steps:

**Clone the Repository**:  
bash  
`git clone https://github.com/Aakvatech-Limited/csf_tz.git`  
**Navigate to the Directory**:  
bash  
`cd csf_tz`  
**Install Dependencies** \- Ensure you have ERPNext and Frappe installed.  
`bench get-app csf_tz`  
**Apply Migrations**  
`bench migrate`  
**Restart Bench**  
`bench restart`

## **Getting Started**

Once installed, you can begin setting up the Tanzanian-specific features:

1. **Configure Electronic Fiscal Devices (EFDs)** \- Navigate to the EFD settings and input your TRA credentials.  
2. **Set Up Tanzanian Tax Rules** \- Customise the tax templates to match local VAT and other tax requirements.  
3. **Localise Financial Settings** \- Configure the Chart of Accounts, bank charges, and currency settings specific to Tanzania.  
4. **Customise Payroll** \- Set up employee data and payroll settings to comply with Tanzanian labour laws.  
5. **Utilise Inventory Tools** \- Use the stock management features to control inventory across multiple Tanzanian locations.

## **Contributing**

We welcome contributions to improve and expand this application. If you have suggestions or improvements, please:

1. Fork the repository.  
2. Create a new branch (`git checkout -b feature-branch`).  
3. Make your changes.  
4. Commit your changes (`git commit -am 'feat: Add new feature'`).  
5. Push to the branch (`git push origin feature-branch`).  
6. Open a Pull Request.

## **Support**

For support and assistance, please create a github issue.

## **Licence**

This project is licensed under the GNU General Public License (GPL). See the LICENCE file for more details.

---

Thank you for choosing Country Specific Functionality Tanzania. We hope this solution enhances your business operations and helps you stay compliant with local regulations\!

