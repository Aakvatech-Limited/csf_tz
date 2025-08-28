import frappe

def execute():

    sql_commands = [
        "ALTER TABLE `tabTransport Assignment` ADD COLUMN `parent` VARCHAR(140) DEFAULT NULL",
        "ALTER TABLE `tabTransport Assignment` ADD COLUMN `parenttype` VARCHAR(140) DEFAULT NULL",
        "ALTER TABLE `tabTransport Assignment` ADD COLUMN `parentfield` VARCHAR(140) DEFAULT NULL",
        "ALTER TABLE `tabTransport Assignment` ADD COLUMN `idx` INT(11) DEFAULT 0",
        "ALTER TABLE `tabTransport Assignment` ADD INDEX `parent` (`parent`)"
    ]

    for sql in sql_commands:
        try:
            frappe.db.sql(sql)
            print("Executed:", sql)
        except Exception as e:
            print("Failed:", sql, "-", str(e))
    frappe.db.commit()
