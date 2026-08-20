frappe.pages['jobcards'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Job Cards',
		single_column: true
	});

	this.page.$JobCards = new frappe.JobCards.job_cards(this.page);


	$("head").append("<link href='/assets/csf_tz/node_modules/vuetify/dist/vuetify.min.css' rel='stylesheet'>");
	$("head").append("<link rel='stylesheet' href='https://fonts.googleapis.com/css?family=Roboto:100,300,400,500,700,900' />");
	$("head").append("<link href='https://cdn.jsdelivr.net/npm/vuetify@2.x/dist/vuetify.min.css' rel='stylesheet'>");
}
