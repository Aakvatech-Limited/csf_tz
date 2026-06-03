<template>
  <v-app>
    <div fluid>
      <H3> Working Job Cards</H3>
      <Card></Card>
      <div v-for="item in data" :key="item.name">
        <div :class="set_status_color(item.status)">
          <v-card class="mb-4">
            <v-list-item three-line>
              <v-row>
                <v-col lg="9" md="9" cols="12">
              <v-list-item-content>
                <div class="overline mb-4">{{ item.name }}</div>
                <v-list-item-title class="headline mb-2">
                  {{ item.operation.name }}
                </v-list-item-title>
                <v-list-item-subtitle class="mb-1">
                  Qty To Manufacture: {{ item.for_quantity }}
                </v-list-item-subtitle>
                <v-list-item-subtitle class="mb-1">
                  Total Completed Qty: {{ item.total_completed_qty }}
                </v-list-item-subtitle>
                <v-list-item-subtitle class="mb-1">
                  Production Item: {{ item.production_item }}
                </v-list-item-subtitle>
                <v-list-item-subtitle class="mb-1">
                  Satus: {{ item.status }}
                </v-list-item-subtitle>
                <v-card-subtitle v-if="item.current_time">
                  Current Time:
                  <span class="hours">{{ get_current(item.current_time).hours }}</span>
                  <span class="colon">:</span>
                  <span class="minutes">{{ get_current(item.current_time).minutes }}</span>
                  <span class="colon">:</span>
                  <span class="seconds">{{ get_current(item.current_time).seconds }}</span>
                  </v-card-subtitle>
              </v-list-item-content>
              </v-col>
              <v-col lg="3" md="3" cols="12">
              <v-img
                max-height="150"
                max-width="250"
                class="img-border mt-5"
                :src="
                  item.operation.image ||
                  '/assets/csf_tz/js/jobcards/placeholder-image.png'
                "
              ></v-img>
              </v-col>
            </v-row>
            </v-list-item>
            <v-card-actions>
              <!-- <v-spacer></v-spacer> -->
              <v-btn text color="primary" @click="open_card(item)">
                open
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
  data: function () {
    return {
      data: "",
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
        callback: function (r) {
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
      hours :
        hours < 10 ? "0" + hours.toString() : hours.toString(),
      minutes :
        minutes < 10 ? "0" + minutes.toString() : minutes.toString(),
      seconds :
        seconds < 10 ? "0" + seconds.toString() : seconds.toString(),
        }
    },
    open_card(item) {
      evntBus.$emit("open_card", item);
    },
    set_status_color(status) {
      if (status == "Open") {
        return "status-Open";
      }
      if (status == "Work In Progress") {
        return "status-Work";
      }
      if (status == "Material Transferred") {
        return "status-Material";
      }
      if (status == "On Hold") {
        return "status-Hold";
      }
      if (status == "Submitted") {
        return "status-Submitted";
      }
    },
  },
  created: function () {
    this.get_data();
    evntBus.$on("show_messag", (msg) => {
      frappe.msgprint(msg);
    });
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
  border: 1px solid #BDBDBD;
}
</style>
