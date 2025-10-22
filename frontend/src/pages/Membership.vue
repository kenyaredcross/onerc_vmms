<template>
  <NoPermission v-if="user?.data == 'Guest'" :page="'Membership'" />
  <div
    class="space-y-4 mx-auto px-4"
    v-if="user?.data && user?.data !== 'Guest'"
  >
    <ErrorMessage
      v-if="currentMembership.error || membershipTypes.error"
      class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20"
      message="Failed to get Membership Details"
    />

    <div
      v-else-if="currentMembership.data"
      class="w-full flex flex-col items-center"
    >
      <Member
        v-if="currentMembership.data.length > 0"
        :membershipStatus="currentMembership.data"
      />
      <EmptyState v-else type="Membership" class="mt-6" />
    </div>

    <div
      v-if="currentMembership.data"
      class="p-2 pt-2 md:p-8 bg-gray-50 rounded-2xl shadow-md text-center mb-20"
    >
      <h1 class="text-3xl font-bold text-gray-800">Select a New Plan</h1>

      <div v-if="membershipTypes.data?.length > 0" class="mt-10">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <div
            v-for="membershipType in membershipTypes.data"
            :key="membershipType.name"
            class="flex justify-center"
          >
            <VmmsPortalCard
              class="w-full max-w-sm transition hover:scale-105 hover:shadow-lg cursor-pointer"
              :membershipType="membershipType"
              @click="selectMembershipType(membershipType)"
            />
          </div>
        </div>
      </div>

      <EmptyState v-else type="Membership Type" class="mt-10" />
    </div>

    <Dialog
      v-model="registerDialog"
      :options="{
        size: 'xl',
      }"
    >
      <template #body-title>
        <h3 class="text-2xl font-bold text-gray-900">
          Register as a <span class="text-red-600">Member</span>
        </h3>
      </template>

      <template #body-content>
        <form @submit.prevent="submit" class="space-y-6">
          <p class="text-gray-600">
            Please fill in the details below to complete your membership
            registration.
          </p>

          <!-- Branch -->
          <div class="bg-white border rounded-lg p-4 shadow-sm">
            <Link
              id="branch"
              :label="'Branch / County'"
              doctype="Company"
              :required="true"
              :filters="{ is_group: 0 }"
              v-model="membershipForm.branch"
              class="w-full"
              :readonly="payNow"
            />
          </div>

          <!-- Membership Info -->
          <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <p class="font-medium text-gray-800">
              Membership Type:
              <span class="text-red-600">
                {{ membershipForm.membership_type }}
              </span>
            </p>
            <p class="text-gray-700 mt-1">
              Amount:
              <span class="font-semibold">KES {{ membershipForm.amount }}</span>
            </p>
          </div>

          <ErrorMessage
            v-if="!payNow && createMembership.error"
            class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm"
            :message="createMembership.error"
          />

          <div
            v-if="!payNow"
            class="flex flex-col sm:flex-row justify-end gap-3 pt-2"
          >
            <Button
              type="button"
              variant="outline"
              theme="red"
              class="rounded-lg px-5"
              @click="cleanUpMembershipForm"
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="solid"
              theme="green"
              :loading="createMembership.loading"
              class="rounded-lg px-6"
            >
              Register
            </Button>
          </div>
          <div v-if="payNow" class="flex flex-col space-y-4">
            <span
              class="text-center text-blue-800 border rounded-md p-2 border-blue-500 bg-blue-50 text-sm"
            >
              Registration Initiated! Please proceed to pay for your membership
              below.
            </span>

            <Input
              :type="'text'"
              :ref_for="true"
              size="sm"
              variant="subtle"
              placeholder="+254123456789"
              :disabled="false"
              label="Enter Mpesa Phone Number to Pay"
              v-model="membershipForm.phone_number"
              required
            />

            <ErrorMessage
              v-if="createMembership.error"
              class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm"
              :message="createMembership.error"
            />

            <div class="flex flex-col sm:flex-row justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                theme="red"
                class="rounded-lg px-5"
                @click="cleanUpMembershipForm"
              >
                Cancel
              </Button>
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
            </div>
          </div>
        </form>
      </template>
    </Dialog>
  </div>
</template>

<script lang="ts" setup>
import { inject, reactive, ref, watch, watchEffect } from "vue";
import { membershipStore } from "../stores/membership";
import {
  Dialog,
  Button,
  createResource,
  ErrorMessage,
  toast,
  Input,
} from "frappe-ui";
import Member from "../components/MemberPlan.vue";
import EmptyState from "../components/EmptyState.vue";
import Link from "../components/Controls/Link.vue";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import { isValidPhone } from "../utils/volunteer";

const { membershipTypes, currentMembership } = membershipStore();
const user = inject<any>("$user");

const registerDialog = ref(false);
const payNow = ref(false);
const membershipForm = reactive({
  membership_type: "",
  amount: 0,
  branch: "",
  member_name: user.data ? user.data.full_name : "",
  email_id: user.data ? user.data.email : "",
  phone_number: "",
});

const createMembership = createResource({
  url: "non_profit.non_profit.user.create_membership",
  onSuccess() {
    toast.success("Membership created successfully");
    currentMembership.reload();
    membershipTypes.reload();
    payNow.value = true;
  },
});

function cleanUpMembershipForm() {
  registerDialog.value = false;
  membershipForm.membership_type = "";
  membershipForm.amount = 0;
  membershipForm.branch = "";
  membershipForm.phone_number = "";
  payNow.value = false;
  createMembership.error = "";
}

function selectMembershipType(membershipType: any) {
  membershipForm.membership_type = membershipType.membership_type;
  membershipForm.amount = membershipType.amount;
  registerDialog.value = true;
}

function submit() {
  if (!membershipForm.branch) {
    createMembership.error = "Please select a branch";
    return;
  }
  createMembership.submit({ ...membershipForm });
}

function payMembership() {
  if (!membershipForm.phone_number) {
    createMembership.error = "Please enter your phone number";
    return;
  }

  if (!isValidPhone(membershipForm.phone_number)) {
    createMembership.error =
      "Please enter a valid Kenyan phone number.eg. (+254123456789)";
    return;
  }
  createMembership.error = "";
  // Logic to pay membership
  alert(
    `Paying for membership with phone number: ${membershipForm.phone_number}`
  );
}

watch(registerDialog, (newValue) => {
  if (newValue === false) {
    cleanUpMembershipForm();
  }
});
</script>
