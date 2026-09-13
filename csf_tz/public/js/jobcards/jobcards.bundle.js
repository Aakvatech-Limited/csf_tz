import { createApp } from "vue";
import "vuetify/styles";
import { createVuetify } from "vuetify";
import JobCardsComponent from "./JobCards.vue";

class JobCardsBuilder {
    constructor({ wrapper, page }) {
        this.$wrapper = $(wrapper);
        this.page = page;
        this.init();
    }

    init() {
        const vuetify = createVuetify();
        const app = createApp(JobCardsComponent);

        app.use(vuetify);
        this.vue = app.mount(this.$wrapper[0]);
    }
}

frappe.provide("frappe.JobCards");
frappe.JobCards.JobCardsBuilder = JobCardsBuilder;
