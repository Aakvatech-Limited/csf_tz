// Job Cards functionality - compatible with Frappe bundling
// This file loads the Vue-based JobCards when needed

frappe.provide('frappe.JobCards');

frappe.JobCards.job_cards = class {
        constructor({ parent }) {
                this.$parent = $(parent);
                this.page = parent.page;
                this.make_body();
        }
        
        make_body() {
                this.$EL = this.$parent.find('.layout-main');
                
                // Check if Vue bundle is available and load Vue component
                if (frappe.JobCards.JobCardsBuilder) {
                    this.load_vue_component();
                } else {
                    // The jobcards.bundle.js should be loaded automatically via hooks.py
                    // If for some reason it's not loaded, show fallback
                    this.load_fallback();
                }
        }
        
        load_vue_component() {
                // Use the Vue-based JobCards builder
                this.vue_builder = new frappe.JobCards.JobCardsBuilder({
                    wrapper: this.$EL[0],
                    page: this.page
                });
        }
        
        load_fallback() {
                // Fallback: Simple placeholder
                this.$EL.html('<div class="job-cards-container"><p>Job Cards functionality loading...</p></div>');
                
                // Try again after a short delay in case the bundle is still loading
                setTimeout(() => {
                    if (frappe.JobCards.JobCardsBuilder) {
                        this.load_vue_component();
                    }
                }, 1000);
        }
        
        setup_header() {
                // Header setup functionality
        }
};