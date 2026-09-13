<template>
  <v-app>
    <div>
      <h3>Working Job Cards</h3>
      <Card />
      <div v-for="item in data" :key="item.name">
        <div :class="set_status_color(item.status)">
          <v-card class="mb-4">
            <v-list-item lines="three">
              <v-row>
                <v-col lg="9" md="9" cols="12">
                  <div class="text-overline mb-4">{{ item.name }}</div>
                  <div class="text-h5 mb-2">{{ item.operation.name }}</div>
                  <div class="text-body-2 mb-1">
                    Qty To Manufacture: {{ item.for_quantity }}
                  </div>
                  <div class="text-body-2 mb-1">
                    Total Completed Qty: {{ item.total_completed_qty }}
                  </div>
                  <div class="text-body-2 mb-1">
                    Production Item: {{ item.production_item }}
                  </div>
                  <div class="text-body-2 mb-1">
                    Status: {{ item.status }}
                  </div>
                  <v-card-subtitle v-if="item.current_time" class="px-0">
                    Current Time:
                    <span class="hours">{{ get_current(item.current_time).hours }}</span>
                    <span class="colon">:</span>
                    <span class="minutes">{{ get_current(item.current_time).minutes }}</span>
                    <span class="colon">:</span>
                    <span class="seconds">{{ get_current(item.current_time).seconds }}</span>
                  </v-card-subtitle>
                </v-col>
                <v-col lg="3" md="3" cols="12">
                  <v-img
                    max-height="150"
                    max-width="250"
                    class="img-border mt-5"
                    :src="item.operation.image || '/assets/csf_tz/js/jobcards/placeholder-image.png'"
                  />
                </v-col>
              </v-row>
            </v-list-item>
            <v-card-actions>
              <v-btn variant="text" color="primary" @click="open_card(item)">
                Open
              </v-btn>
            </v-card-actions>
          </v-card>
        </div>
      </div>
    </div>
  </v-app>
</template>

<script>
import { evntBus } from "./bus";
import Card from "./Card.vue";

export default {
  data() {
    return {
      data: [],
    };
  },
  components: {
    Card,
  },
  methods: {
    get_data() {
      const vm = this;
      frappe.call({
        method: "csf_tz.csf_tz.page.jobcards.jobcards.get_job_cards",
        args: {},
        async: true,
        callback(r) {
          if (r.message) {
            vm.data = r.message;
          }
        },
      });
    },
    get_current(increment) {
      const hours = Math.floor(increment / 3600);
      const minutes = Math.floor((increment - hours * 3600) / 60);
      const seconds = increment - hours * 3600 - minutes * 60;
      return {
        hours: hours < 10 ? "0" + hours.toString() : hours.toString(),
        minutes: minutes < 10 ? "0" + minutes.toString() : minutes.toString(),
        seconds: seconds < 10 ? "0" + seconds.toString() : seconds.toString(),
      };
    },
    open_card(item) {
      evntBus.$emit("open_card", item);
    },
    set_status_color(status) {
      if (status === "Open") return "status-Open";
      if (status === "Work In Progress") return "status-Work";
      if (status === "Material Transferred") return "status-Material";
      if (status === "On Hold") return "status-Hold";
      if (status === "Submitted") return "status-Submitted";
      return "";
    },
  },
  created() {
    this.get_data();
    this.showMessageHandler = (msg) => frappe.msgprint(msg);
    evntBus.$on("show_messag", this.showMessageHandler);
  },
  beforeUnmount() {
    evntBus.$off("show_messag", this.showMessageHandler);
  },
};
</script>

<style>
.navbar-default {
  height: 40px;
}
div.navbar .container {
  padding-top: 2px;
}
.status-Open {
  border-left: 5px solid purple;
}
.status-Work {
  border-left: 5px solid lime;
}
.status-Material {
  border-left: 5px solid teal;
}
.status-Hold {
  border-left: 5px solid #607d8b;
}
.status-Submitted {
  border-left: 5px solid #ff5722;
}
.img-border {
  border: 1px solid #bdbdbd;
}
</style>
