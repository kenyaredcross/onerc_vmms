<template>
  <div
    v-if="membershipTypes.data?.length > 0"
    class="flex justify-center mt-10"
  >
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <router-link
        v-for="membershipType in membershipTypes.data"
        :key="membershipType.name"
        :to="{ name: 'Login', hash: '#signup' }"
        class="flex justify-center"
      >
        <VmmsPortalCard :membershipType="membershipType" />
      </router-link>
    </div>
  </div>
  <EmptyState v-else type="" />

  <div class="t py-16">
    <div
      class="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between px-6"
    >
      <div>
        <h2 class="text-3xl md:text-4xl font-bold m-2">
          Sign up to be a volunteer today!
        </h2>
        <router-link :to="{ name: 'Login', hash: '#signup' }">
          <Button
            :variant="'solid'"
            :ref_for="true"
            theme="gray"
            size="lg"
            label="Button"
            :loading="false"
            :disabled="false"
            tooltip="Hover for more!"
          >
            Sign up
          </Button>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { RouterLink } from "vue-router";
import Button from "frappe-ui/src/components/Button/Button.vue";
import EmptyState from "../components/EmptyState.vue";
import VmmsPortalCard from "../components/VmmsPortalCard.vue";
import { membershipStore } from "../stores/membership";

const { membershipTypes } = membershipStore();
</script>
