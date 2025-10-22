<template>
  <div
    v-if="!roleResource.data.is_pending_approval"
    class="h-[75vh] bg-gray-50 flex items-center justify-center"
  >
    <div class="max-w-6xl w-full grid grid-cols-1 md:grid-cols-2 gap-12 p-10">
      <div class="flex flex-col justify-center space-y-6 text-left">
        <h1
          class="text-3xl md:text-6xl font-extrabold text-red-600 leading-tight"
        >
          Kenya Red Cross <br />
          <span class="text-gray-800">Society</span>
        </h1>
        <p class="text-lg text-gray-700 max-w-lg">
          🌍 Together, we can
          <span class="font-semibold text-red-500">save lives</span>, support
          communities, and make a
          <span class="font-semibold text-red-500">real difference</span>. Come
          be part of our mission as a
          <span class="font-semibold text-red-500">volunteer</span> ✨ or a
          <span class="font-semibold text-red-500">member</span> 🤝!
        </p>
        <p class="text-gray-600 max-w-md">
          Your time and passion can help change lives. Join us today and help
          build stronger, safer communities for everyone.
        </p>
      </div>

      <!-- Right Section: Actions -->
      <div class="flex flex-col items-center justify-center space-y-6">
        <div class="space-y-4 w-full max-w-sm">
          <Button
            variant="solid"
            theme="red"
            icon-right="arrow-right"
            class="w-full py-4 rounded-xl shadow-lg text-lg font-medium"
            @click="navigateTo('volunteer/signup')"
          >
            🙋‍♂️ Join as Volunteer
          </Button>
          <Button
            variant="outline"
            theme="red"
            icon-right="arrow-right"
            class="w-full py-4 rounded-xl shadow-md text-lg font-medium"
            @click="navigateTo('membership')"
          >
            🏅 Join as Member
          </Button>
        </div>
      </div>
    </div>
  </div>

  <PendingApproval v-else-if="roleResource.data.is_pending_approval" />
</template>

<script lang="ts" setup>
import { Button } from "frappe-ui";
import router from "../router";
import { usersStore } from "../stores/user";
import PendingApproval from "./PendingApproval.vue";

const { roleResource } = usersStore();

function navigateTo(path: string) {
  router.push("/" + path);
}
</script>
