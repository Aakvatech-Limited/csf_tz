$(document).on('app_ready', function () {
    frappe.router.on("change", () => {
        var route = frappe.get_route();
        if (route && route[0] == "Form") {
            frappe.ui.form.on(route[1], {
                refresh: function (frm) {
                    frm.page.add_menu_item(__("AI Assist: Explain Doctype"), function () {   
                        let dialog = new frappe.ui.Dialog({
                            title: __("AI Assist - DocType User Manual"),
                            size: "large",
                            fields: [
                                {
                                    fieldname: "response",
                                    label: __("Response"),
                                    fieldtype: "HTML"
                                }
                            ],
                            secondary_action_label: __("Close"),
                            secondary_action: function() {
                                dialog.hide();
                            }
                        });
                        
                        let data = {
                            doctype: frm.doc.doctype,
                            name: frm.doc.name,
                            title: frm.doc.title || frm.doc.name,
                            fields: {}
                        };
                        
                        for (let field of frm.meta.fields) {
                            if (frm.doc[field.fieldname] && field.fieldtype !== "Section Break" && field.fieldtype !== "Column Break") {
                                data.fields[field.fieldname] = {
                                    value: frm.doc[field.fieldname],
                                    label: field.label,
                                    fieldtype: field.fieldtype
                                };
                            }
                        }
                        doctype_prompt = `Create user manual with below headings:
                                        1. Overview
                                        2. Key Features
                                        3. Pre-Requisites
                                        4. Step-by-Step Usage
                                        5. Script Customizations
                                        6. Troubleshooting (Common Errors and Resolutions)
                                        7. User Roles and Permissions
                                        8. Key Notes
                                        9. What business process pain point does it help remove`                             
                        frappe.call({
                            method: "csf_tz.ai_integration.api.openai.analyze_doctype_with_openai",
                            args: {
                                doctype_name: frm.doc.doctype,
                                prompt: doctype_prompt
                            },
                            freeze: true,
                            freeze_message: __("Analyzing..."),
                            callback: function(r) {
                                if (r.message) {
                                    // Convert Markdown to HTML using Frappe's built-in function
                                    let htmlContent = frappe.markdown(r.message);
                                    dialog.set_value("response", htmlContent);
                                }
                                
                                frappe.utils.play_sound("submit");
                                dialog.show();
                                
                                frappe.show_alert({
                                    message: __("Analysis completed successfully!"),
                                    indicator: "green"
                                });
                            },
                            error: function(r) {
                                console.error("OpenAI API Error:", r);
                                
                                dialog.set_value("response", __("Error occurred while analyzing. Please check the console for details."));
                                
                                frappe.show_alert({
                                    message: __("Analysis failed. Please try again."),
                                    indicator: "red"
                                });
                            }
                        });
                    });
                    
                    frm.page.add_menu_item(__("AI Assist: Explain This Document"), function () { 
                        let dialog = new frappe.ui.Dialog({
                            title: __("AI Assist - Document Analysis"),
                            size: "large",
                            fields: [
                                {
                                    fieldname: "response",
                                    label: __("Response"),
                                    fieldtype: "HTML"
                                }
                            ],
                            secondary_action_label: __("Close"),
                            secondary_action: function() {
                                dialog.hide();
                            }
                        });
                        
                        let data = {
                            doctype: frm.doc.doctype,
                            name: frm.doc.name,
                            title: frm.doc.title || frm.doc.name,
                            fields: {}
                        };
                        
                        for (let field of frm.meta.fields) {
                            if (frm.doc[field.fieldname] && field.fieldtype !== "Section Break" && field.fieldtype !== "Column Break") {
                                data.fields[field.fieldname] = {
                                    value: frm.doc[field.fieldname],
                                    label: field.label,
                                    fieldtype: field.fieldtype
                                };
                            }
                        }
                        
                        document_prompt = `You are a business analyst reviewing a document from an ERP system (ERPNext). You will receive a single submitted document in JSON format (such as a Sales Invoice, Journal Entry, Material Request, etc.). Using only the information in the document:
                                        1. Identify and summarize the document's business purpose.
                                        2. Identify any key parties (customers, suppliers, employees, etc.).
                                        3. Note the financial and operational impact of the transaction (revenue, expense, taxes, stock movements).
                                        4. Highlight any references or linked documents if they appear.
                                        5. Point out any exceptions, risks, or data that might require attention (e.g., overdue, missing links, mismatched status).
                                        6. Conclude with what business outcome this document supports.

                                        Avoid technical or database terminology. Your response should be suitable for a business operations manager. Write clearly, use bullets or short paragraphs, and name the document type and ID.

                                        Document JSON:`

                        frappe.call({
                            method: "csf_tz.ai_integration.api.openai.analyze_doctype_with_openai",
                            args: {
                                doctype_name: frm.doc.doctype,
                                prompt: document_prompt,
                                doc_data: JSON.stringify(data)
                            },
                            freeze: true,
                            freeze_message: __("Analyzing..."),
                            callback: function(r) {
                                if (r.message) {
                                    // Convert Markdown to HTML using Frappe's built-in function
                                    let htmlContent = frappe.markdown(r.message);
                                    dialog.set_value("response", htmlContent);
                                }
                                
                                frappe.utils.play_sound("submit");
                                dialog.show();
                                
                                frappe.show_alert({
                                    message: __("Analysis completed successfully!"),
                                    indicator: "green"
                                });
                            },
                            error: function(r) {
                                console.error("OpenAI API Error:", r);
                                
                                dialog.set_value("response", __("Error occurred while analyzing. Please check the console for details."));
                                
                                frappe.show_alert({
                                    message: __("Analysis failed. Please try again."),
                                    indicator: "red"
                                });
                            }
                        });
                    });
                }
            });
        }
    });
});
