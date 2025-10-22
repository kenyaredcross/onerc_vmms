<template>
  <div class="flex flex-col gap-4 md:gap-8 md:p-6">
    <h1
      v-if="membershipList.data && membershipList.data.length > 0"
      class="text-3xl font-bold text-gray-800"
    >
      Your Memberships
    </h1>
    <div
      v-if="membershipList.data && membershipList.data.length > 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <Card
        v-for="membership in membershipList.data"
        :key="membership.name"
        class="flex flex-col rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 group"
      >
        <!-- Header -->
        <div class="p-6 border-b bg-gray-50 flex justify-between items-center">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ membership.membership_type }}
          </h2>
          <Badge
            :variant="'subtle'"
            :theme="
              getMembershipStatusTheme(membership.membership_status || '')
            "
            size="lg"
            class="border text-sm"
          >
            {{ membership.membership_status }}
          </Badge>
        </div>

        <!-- Body -->
        <div class="p-6 flex flex-col gap-4 flex-1">
          <!-- Dates -->
          <div class="flex justify-between text-sm text-gray-600">
            <div>
              <span class="block text-gray-500">Start</span>
              <span class="font-medium text-gray-800">
                {{ formatDate(membership.from_date) }}
              </span>
            </div>
            <div>
              <span class="block text-gray-500">Renewal Due</span>
              <span class="font-medium text-gray-800">
                {{ formatDate(membership.to_date) }}
              </span>
            </div>
          </div>

          <!-- Branch + Amount -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div>
              <span class="block text-gray-500">Branch / County</span>
              <span class="font-medium text-gray-800">
                {{ membership.company }}
              </span>
            </div>
            <div>
              <span class="block text-gray-500">Amount</span>
              <span class="font-semibold text-gray-900 text-lg">
                KES {{ membership.amount }}
              </span>
            </div>
          </div>
        </div>

        <!-- CTA Footer -->
        <div class="bg-gray-50 p-4 border-t">
          <Button
            :variant="'solid'"
            theme="red"
            class="w-full"
            @click="payNow = true"
          >
            Renew Membership
          </Button>
        </div>
      </Card>
    </div>
    <div
      v-if="
        membershipList.data &&
        membershipList.data.length > 0 &&
        roleResource.data &&
        !roleResource.data.is_volunteer
      "
      class="flex flex-col md:flex-row items-center justify-between gap-6 rounded-2xl border border-red-200 bg-gradient-to-r from-red-50 to-white p-6 md:p-8 shadow-md"
    >
      <!-- Left Section -->
      <div class="text-center md:text-left flex-1">
        <!-- Heading -->
        <h2 class="text-2xl md:text-3xl font-extrabold text-gray-900 mb-2">
          Become a <span class="text-red-600">Volunteer</span>
        </h2>

        <!-- Subtext -->
        <p class="text-gray-700 max-w-2xl leading-relaxed">
          Join the <span class="font-semibold">Kenya Red Cross Society</span> as
          a volunteer and support your community. Contribute to
          <span class="text-red-600 font-medium">life-saving services</span>,
          gain valuable <span class="font-medium">skills</span>, and be part of
          a <span class="italic">global humanitarian movement</span>.
        </p>
      </div>

      <!-- Right Section (CTA) -->
      <div class="flex-shrink-0">
        <RouterLink :to="{ name: 'VolunteerSignup' }">
          <Button
            variant="solid"
            theme="red"
            icon-right="arrow-right"
            class="px-8 py-3 rounded-xl text-base font-semibold shadow-md hover:shadow-lg transition-all"
          >
            Register
          </Button>
        </RouterLink>
      </div>
    </div>
  </div>
  <Dialog v-model="payNow">
    <template #body-title>
      <h3 class="text-2xl text-gray-900">
        <span class="text-red-600">Enter Mpesa Phone Number to Pay</span>
      </h3>
    </template>

    <template #body-content>
      <form @submit.prevent="payMembership" class="space-y-3">
        <Input
          required
          :type="'text'"
          :ref_for="true"
          size="sm"
          variant="subtle"
          placeholder="+254123456789"
          :disabled="false"
          label="Phone Number"
          v-model="phoneNumber"
        />
        <ErrorMessage v-if="errorMessage" :message="errorMessage" />
        <Button
          type="button"
          variant="solid"
          theme="red"
          icon-right="credit-card"
          class="rounded-lg px-6"
          @click="payMembership"
        >
          Pay Now
        </Button>
      </form>
    </template>
  </Dialog>
</template>

<script lang="ts" setup>
import {
  Badge,
  Card,
  createResource,
  Dialog,
  Button,
  Input,
  ErrorMessage,
} from "frappe-ui";
import { RouterLink } from "vue-router";
import { usersStore } from "../stores/user";
import { ref } from "vue";
import { isValidPhone } from "../utils/volunteer";

const { roleResource } = usersStore();

const payNow = ref(false);
const phoneNumber = ref("");
const errorMessage = ref("");

interface Membership {
  name?: string;
  membership_type?: string;
  from_date?: string;
  to_date?: string;
  membership_status?: string;
  amount?: number;
  company?: string;
  type_details?: Record<string, any>;
}

const membershipList = createResource<Membership[]>({
  url: "non_profit.non_profit.api.get_current_membership",
  auto: true,
  cache: ["currentMembership"],
});

function getMembershipStatusTheme(status: string) {
  switch (status) {
    case "Current":
      return "green";
    case "Expired":
      return "red";
    case "Pending":
      return "orange";
    case "Cancelled":
      return "gray";
    default:
      return "gray";
  }
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function payMembership() {
  if (!phoneNumber.value) {
    errorMessage.value = "Please enter your phone number";
    return;
  }

  if (!isValidPhone(phoneNumber.value)) {
    errorMessage.value =
      "Please enter a valid Kenyan phone number.eg. (+254123456789)";
    return;
  }

  errorMessage.value = "";
  alert(`Paying for membership with phone number: ${phoneNumber.value}`);
}
</script>
