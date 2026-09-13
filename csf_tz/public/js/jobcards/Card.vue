<template>
  <div v-if="Dialog" class="d-flex justify-center">
    <v-dialog v-model="Dialog" max-width="900">
      <v-card class="px-3">
        <v-card-title class="mt-2">
          <span class="text-h5 text-indigo">{{ cardData.operation.name }}</span>
          <v-spacer />
          <div
            class="stopwatch"
            style="font-weight: bold; margin: 0 13px 0 2px; color: #545454; font-size: 18px; display: inline-block; vertical-align: text-bottom;"
          >
            <span class="hours">{{ timer.hours }}</span>
            <span class="colon">:</span>
            <span class="minutes">{{ timer.minutes }}</span>
            <span class="colon">:</span>
            <span class="seconds">{{ timer.seconds }}</span>
          </div>
          <v-spacer />
          <span class="text-overline">{{ cardData.name }}</span>
        </v-card-title>

        <v-row class="mx-3">
          <v-col lg="5" md="5" cols="12">
            <div class="text-subtitle-1 mb-1">Status: {{ cardData.status }}</div>
          </v-col>
          <v-col lg="4" md="4" cols="12">
            <v-textarea
              label="Operation Description"
              auto-grow
              variant="outlined"
              rows="3"
              row-height="25"
              readonly
              v-model="cardData.operation.description"
              hide-details
            />
          </v-col>
          <v-col lg="3" md="3" cols="12">
            <div class="text-subtitle-1 mb-1">Production Item: {{ cardData.production_item }}</div>
            <v-divider />
            <v-autocomplete
              density="compact"
              auto-select-first
              variant="outlined"
              color="indigo"
              label="Team Leader"
              v-model="cardData.employee"
              :items="employees"
              :item-title="employeeItemTitle"
              item-value="name"
              bg-color="white"
              no-data-text="Employee not found"
              hide-details
              :readonly="Boolean(cardData.employee)"
            >
              <template #item="{ props, item }">
                <v-list-item
                  v-bind="props"
                  :title="item.raw.name"
                  :subtitle="item.raw.employee_name"
                />
              </template>
            </v-autocomplete>
          </v-col>
        </v-row>

        <v-row class="mx-3">
          <v-col lg="9" md="9" cols="12">
            <v-autocomplete
              density="compact"
              auto-select-first
              variant="outlined"
              color="indigo"
              label="Station Members"
              v-model="members"
              :items="employees"
              :item-title="employeeItemTitle"
              item-value="name"
              bg-color="white"
              no-data-text="Employee not found"
              hide-details
              multiple
            >
              <template #item="{ props, item }">
                <v-list-item
                  v-bind="props"
                  :title="item.raw.name"
                  :subtitle="item.raw.employee_name"
                />
              </template>
            </v-autocomplete>
          </v-col>
          <v-col lg="9" md="9" cols="12">
            <v-textarea
              class="my-2"
              label="Remarks"
              auto-grow
              variant="outlined"
              rows="2"
              row-height="25"
              v-model="cardData.remarks"
              hide-details
            />
          </v-col>
          <v-col lg="3" md="3" cols="12">
            <div class="text-subtitle-1 mb-1">Qty To Manufacture: {{ cardData.for_quantity }}</div>
            <div class="text-subtitle-1 mb-1">Qty Completed: {{ cardData.total_completed_qty }}</div>
          </v-col>
        </v-row>

        <v-card-actions class="mx-3">
          <v-btn
            v-if="!cardData.job_started && cardData.total_completed_qty != cardData.for_quantity"
            @click="start_por"
            color="success"
            variant="flat"
          >
            Start
          </v-btn>
          <v-btn
            v-if="cardData.status == 'On Hold' && cardData.total_completed_qty != cardData.for_quantity"
            @click="resume_por"
            color="warning"
            variant="flat"
          >
            Resume
          </v-btn>
          <v-btn
            v-if="cardData.status == 'Work In Progress' && cardData.total_completed_qty != cardData.for_quantity"
            @click="pause_por"
            color="warning"
            variant="flat"
          >
            Stop
          </v-btn>
          <v-spacer />
          <v-text-field
            v-if="cardData.status == 'Work In Progress' && cardData.total_completed_qty != cardData.for_quantity"
            variant="outlined"
            color="indigo"
            label="Completed Qty"
            bg-color="white"
            hide-details
            v-model="completed_qty"
            type="number"
            density="compact"
          />
          <v-spacer />
          <v-btn
            color="primary"
            variant="flat"
            @click="submit_dialog"
            v-if="cardData.total_completed_qty == cardData.for_quantity && cardData.status != 'Completed'"
          >
            Submit
          </v-btn>
          <v-btn color="error" variant="flat" @click="close_dialog">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { evntBus } from "./bus";

export default {
  data: () => ({
    Dialog: false,
    cardData: { operation: {} },
    employees: [],
    members: [],
    completed_qty: 1,
    timer: {
      hours: "00",
      minutes: "00",
      seconds: "00",
      interval: null,
    },
  }),
  watch: {
    Dialog(value) {
      if (value) {
        this.get_employees();
      } else {
        clearInterval(this.timer.interval);
      }
    },
  },
  methods: {
    employeeItemTitle(item) {
      return item.employee_name ? `${item.name} - ${item.employee_name}` : item.name;
    },
    close_dialog() {
      this.Dialog = false;
    },
    start_job() {
      const row = frappe.model.add_child(this.cardData, "Job Card Time Log", "time_logs");
      row.from_time = frappe.datetime.now_datetime();
      row.name = "";
      row.completed_qty = 1;
      this.cardData.job_started = 1;
      this.cardData.started_time = row.from_time;
      this.cardData.status = "Work In Progress";
      if (!frappe.flags.resume_job) {
        this.cardData.current_time = 0;
      }
      this.set_timer();
      this.save();
    },
    start_por() {
      if (!this.cardData.employee) {
        evntBus.$emit("show_messag", "Please set Employee");
      } else {
        this.start_job();
      }
    },
    resume_por() {
      frappe.flags.resume_job = 1;
      this.start_job();
    },
    pause_por() {
      if (this.cardData.for_quantity < this.cardData.total_completed_qty + flt(this.completed_qty)) {
        evntBus.$emit(
          "show_messag",
          "The completed quantity cannot be greater than the required quantity"
        );
        return;
      }
      frappe.flags.pause_job = 1;
      this.cardData.status = "On Hold";
      clearInterval(this.timer.interval);
      this.complete_job();
    },
    get_employees() {
      const vm = this;
      let employees = [];
      frappe.call({
        method: "csf_tz.csf_tz.page.jobcards.jobcards.get_employees",
        args: { company: this.cardData.company },
        async: false,
        callback(r) {
          if (r.message) {
            employees = r.message;
          }
        },
      });
      vm.employees = employees;
    },
    set_timer() {
      if (this.cardData.status == "Completed") {
        return;
      }
      const vm = this;
      let currentIncrement = this.cardData.current_time || 0;
      if (this.cardData.started_time || this.cardData.current_time) {
        if (this.cardData.status == "On Hold") {
          updateStopwatch(currentIncrement);
          clearInterval(this.timer.interval);
        } else {
          currentIncrement += moment(frappe.datetime.now_datetime()).diff(
            moment(this.cardData.started_time),
            "seconds"
          );
          initialiseTimer();
        }

        function initialiseTimer() {
          clearInterval(vm.timer.interval);
          vm.timer.interval = setInterval(() => {
            currentIncrement += 1;
            updateStopwatch(currentIncrement);
          }, 1000);
        }

        function updateStopwatch(increment) {
          const hours = Math.floor(increment / 3600);
          const minutes = Math.floor((increment - hours * 3600) / 60);
          const seconds = increment - hours * 3600 - minutes * 60;

          vm.timer.hours = hours < 10 ? "0" + hours.toString() : hours.toString();
          vm.timer.minutes = minutes < 10 ? "0" + minutes.toString() : minutes.toString();
          vm.timer.seconds = seconds < 10 ? "0" + seconds.toString() : seconds.toString();
        }
      }
    },
    complete_job(completed_time) {
      const idx = this.cardData.time_logs.length - 1;
      this.cardData.time_logs[idx].completed_qty = flt(this.completed_qty);
      this.completed_qty = 1;
      this.cardData.time_logs.forEach((d) => {
        if (d.from_time && !d.to_time) {
          d.to_time = completed_time || frappe.datetime.now_datetime();

          if (frappe.flags.pause_job) {
            const currentIncrement = moment(d.to_time).diff(moment(d.from_time), "seconds") || 0;
            this.cardData.current_time = currentIncrement + (this.cardData.current_time || 0);
          } else {
            this.cardData.started_time = "";
            this.cardData.job_started = 0;
            this.cardData.current_time = 0;
          }
          this.save();
        }
      });
    },
    submit_dialog() {
      this.cardData.status = "Completed";
      this.save("Submit");
      this.close_dialog();
    },
    save(action = "Save") {
      const vm = this;
      const doc = { ...this.cardData };
      doc.members = [];
      this.members.forEach((element) => {
        const employee = this.employees.find((emp) => emp.name == element);
        doc.members.push({
          employee: element,
          employee_name: employee ? employee.employee_name : "",
        });
      });

      delete doc.operation;
      frappe.call({
        method: "csf_tz.csf_tz.page.jobcards.jobcards.save_doc",
        args: {
          doc,
          action,
        },
        async: false,
        callback(r) {
          if (r.message) {
            r.message.operation = vm.cardData.operation;
            vm.members = [];
            r.message.members.forEach((element) => {
              vm.members.push(element.employee);
            });
            Object.assign(vm.cardData, r.message);
          }
        },
      });
    },
  },
  created() {
    this.openCardHandler = (job_card) => {
      const vm = this;
      this.Dialog = true;
      this.cardData = job_card;
      this.members = [];
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Job Card",
          name: job_card.name,
        },
        callback(r) {
          if (r.message) {
            vm.cardData = r.message;
            r.message.members.forEach((element) => {
              vm.members.push(element.employee);
            });
            vm.timer = {
              hours: "00",
              minutes: "00",
              seconds: "00",
              interval: null,
            };
            vm.set_timer();
          }
        },
      });
    };
    evntBus.$on("open_card", this.openCardHandler);
  },
  beforeUnmount() {
    clearInterval(this.timer.interval);
    evntBus.$off("open_card", this.openCardHandler);
  },
};
</script>
