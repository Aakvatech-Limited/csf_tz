$(document).on('app_ready', function () {
	frappe.router.on("change", () => {
		var route = frappe.get_route();
		if (route && route[0] == "Form") {
			frappe.ui.form.on(route[1], {
				refresh: function (frm) {
                    frm.page.add_menu_item(__("AI Assist: Explain Doctype"), function () {
                        let dialog = new frappe.ui.Dialog({
                            title: __("AI Assist - DocType Analysis"),
                            size: "large",
                            fields: [
                                {
                                    fieldname: "doctype_name",
                                    label: __("DocType Name"),
                                    fieldtype: "Link",
                                    options: "DocType",
                                    reqd: 1,
                                    default: frm.doc.doctype,
                                    description: __("Select the DocType you want to analyze")
                                },
                                {
                                    fieldname: "prompt",
                                    label: __("Analysis Prompt"),
                                    fieldtype: "Text",
                                    reqd: 1,
                                    default: __("Explain this DocType including its purpose, all fields, and relationships with other erpnext doctypes."),
                                    description: __("Enter what you want to know about this DocType")
                                },
                                {
                                    fieldname: "response_section",
                                    fieldtype: "Section Break",
                                    label: __("AI Response")
                                },
                                {
                                    fieldname: "response",
                                    label: __("Response"),
                                    fieldtype: "HTML",
                                    description: __("AI response will appear here")
                                }
                            ],
                            secondary_action_label: __("Close"),
                            secondary_action: function() {
                                dialog.hide();
                            },
                            primary_action_label: __("Analyze"),
                            primary_action: function(values) {
                                if (!values.doctype_name || !values.prompt) {
                                    frappe.msgprint(__("Please fill all required fields"));
                                    return;
                                }
                                
                                // Store reference to original analyze function
                                let originalAnalyzeFunction = arguments.callee;
                                
                                dialog.set_value("response", __("Analyzing... Please wait."));
                                
                                dialog.set_primary_action(__("Analyzing..."));
                                dialog.primary_action = null;
                                
                                frappe.call({
                                    method: "csf_tz.ai_integration.api.openai.analyze_doctype_with_openai",
                                    args: {
                                        doctype_name: values.doctype_name,
                                        prompt: values.prompt
                                    },
                                    freeze: true,
                                    freeze_message: __("Analyzing..."),
                                    callback: function(r) {
                                        if (r.message) {
                                            let htmlContent = frappe.markdown(r.message);
                                            dialog.set_value("response", htmlContent);
                                            
                                            dialog.get_field("doctype_name").toggle(false);
                                            dialog.get_field("prompt").toggle(false);
                                            
                                            dialog.set_primary_action(__("Try Again"), function() {
                                                dialog.get_field("doctype_name").toggle(true);
                                                dialog.get_field("prompt").toggle(true);
                                                
                                                dialog.set_value("response", "");
                                                
                                                dialog.set_primary_action(__("Analyze"), originalAnalyzeFunction);
                                                
                                                dialog.get_field("doctype_name").set_focus();
                                            });
                                            
                                            frappe.utils.play_sound("submit");
                                            frappe.show_alert({
                                                message: __("Analysis completed successfully!"),
                                                indicator: "green"
                                            });
                                        }
                                    },
                                    error: function(r) {
                                        console.error("OpenAI API Error:", r);
                                        
                                        dialog.set_value("response", __("Error occurred while analyzing. Please check the console for details."));
                                        
                                        dialog.get_field("doctype_name").toggle(false);
                                        dialog.get_field("prompt").toggle(false);
                                        
                                        dialog.set_primary_action(__("Try Again"), function() {
                                            dialog.get_field("doctype_name").toggle(true);
                                            dialog.get_field("prompt").toggle(true);
                                            
                                            dialog.set_value("response", "");
                                            
                                            dialog.set_primary_action(__("Analyze"), originalAnalyzeFunction);
                                            
                                            dialog.get_field("doctype_name").set_focus();
                                        });
                                        
                                        frappe.show_alert({
                                            message: __("Analysis failed. Please try again."),
                                            indicator: "red"
                                        });
                                    }
                                });
                            },
                        });
                        
                        dialog.set_value("doctype_name", frm.doc.doctype);
                        dialog.get_field("doctype_name").set_focus();
                        dialog.show();
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
                        
                        frappe.call({
                            method: "csf_tz.ai_integration.api.openai.analyze_doctype_with_openai",
                            args: {
                                doctype_name: frm.doc.doctype,
                                prompt: "Explain this frappe document form including detail of each field in the document",
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
