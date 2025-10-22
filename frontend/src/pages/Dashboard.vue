<template>
  <NoPermission v-if="user?.data == 'Guest'" :page="'Dashboard'" />
  <div v-if="user?.data && user?.data !== 'Guest'" class="max-w-7xl mx-auto">
    <div class="flex flex-col gap-2 my-6">
      <h1 class="text-3xl md:text-4xl font-bold text-gray-900">
        👋 Welcome back, {{ user?.data?.full_name }}!
      </h1>
    </div>

    <div v-if="roleResource?.loading" class="text-center py-20">
      <p>Setting Up Dashboard...</p>
      <ProgressSpinner />
    </div>

    <div v-else-if="roleResource?.data">
      <Welcome
        v-if="
          !roleResource?.data?.is_volunteer && !roleResource?.data?.is_member
        "
      />
      <div v-if="roleResource?.data" class="mb-8 h-full">
        <Volunteer
          v-if="roleResource?.data?.is_volunteer"
          v-bind="dashboardStats?.data"
        />

        <Member
          :membership-status="currentMembership?.data"
          v-else-if="roleResource?.data?.is_member"
        />
      </div>

      <section
        v-if="
          roleResource?.data &&
          (roleResource?.data?.is_volunteer || roleResource?.data?.is_member)
        "
        class="flex flex-col gap-4 md:p-6 bg-white shadow"
      >
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-semibold text-gray-900">Upcoming Events</h2>
          <router-link to="/events">
            <button
              class="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
            >
              View All
              <ChevronRight class="w-4 h-4" />
            </button>
          </router-link>
        </div>

        <div
          v-if="events?.data && events?.data.length > 0 && !toggleEventView"
          class="grid md:grid-cols-3 gap-4"
        >
          <EventCard
            v-for="event in events?.data.slice(0, 3)"
            :key="event.name"
            :event="event"
          />
        </div>

        <EventCalendar v-if="toggleEventView" :event="events?.data" />

        <EmptyState
          v-if="events?.data && events?.data.length === 0"
          type="Events"
        />
      </section>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ChevronRight } from "lucide-vue-next";
import { createResource } from "frappe-ui";

import EventCard from "../components/EventCard.vue";
import EventCalendar from "../components/EventCalendar.vue";
import Member from "../components/MemberPlan.vue";
import Volunteer from "../components/Volunteer.vue";
import Welcome from "../components/Welcome.vue";
import EmptyState from "../components/EmptyState.vue";

import router from "../router";
import { usersStore } from "../stores/user";
import { membershipStore } from "../stores/membership";
import { sessionStore } from "../stores/session";

import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import NoPermission from "../components/NoPermission.vue";

const { roleResource, userResource } = usersStore();
const { events, currentMembership } = membershipStore();
const { isLoggedIn } = sessionStore();

const toggleEventView = ref(false);
const user = userResource;

onMounted(() => {
  if (isLoggedIn) {
    roleResource.reload();
    currentMembership.reload();
    events.reload();
  }
});

const dashboardStats = createResource({
  url: "non_profit.non_profit.api.get_dashboard_stats",
  auto: true,
});

function toggleEventViews() {
  toggleEventView.value = !toggleEventView.value;
}
</script>

<style scoped>
.max-h-screen::-webkit-scrollbar {
  width: 8px;
}
.max-h-screen::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}
</style>
