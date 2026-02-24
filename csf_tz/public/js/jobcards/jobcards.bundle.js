import { createApp } from "vue";
import { createVuetify } from 'vuetify';
import JobCardsComponent from './JobCards.vue';

class JobCardsBuilder {
    constructor({ wrapper, page }) {
        this.$wrapper = $(wrapper);
        this.page = page;
        this.init();
    }
    
    init() {
        // Create Vuetify instance
        const vuetify = createVuetify();
        
        // Create Vue app
        const app = createApp(JobCardsComponent);
        
        // Use Vuetify
        app.use(vuetify);
        
        // Mount the app
        this.vue = app.mount(this.$wrapper[0]);
    }
}

// Export the class
frappe.provide('frappe.JobCards');
frappe.JobCards.JobCardsBuilder = JobCardsBuilder;
