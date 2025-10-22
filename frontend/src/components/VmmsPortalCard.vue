<template>
  <Card
    class="flex flex-col w-full rounded-2xl p-4 h-full shadow-sm hover:shadow-md transition-all duration-500 group cursor-pointer"
  >
    <!-- Membership Info -->
    <div class="mb-4">
      <div class="bg-gray-50 rounded-xl p-4 border border-gray-100">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">
          {{ membershipType.membership_type }}
        </h3>
      </div>
    </div>

    <!-- Details -->
    <div
      class="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-6 text-sm text-gray-600 mb-6"
    >
      <div class="flex flex-col sm:col-span-2">
        <span class="text-gray-500">Amount</span>
        <span class="font-semibold text-gray-900 text-lg">
          KES {{ membershipType.amount }} <span class="text-sm">/year</span>
        </span>
      </div>

      <div class="flex flex-col sm:col-span-2">
        <span class="text-gray-500">Benefits</span>
        <ul
          class="list-disc list-inside text-left text-gray-700 space-y-1 mt-1"
        >
          <li v-for="benefit in membershipType.benefits" :key="benefit">
            {{ benefit }}
          </li>
        </ul>
      </div>
    </div>

    <!-- Action Button -->
    <div class="mt-auto">
      <Button variant="solid" theme="red" class="w-full"> Select Plan </Button>
    </div>
  </Card>
</template>

<script lang="ts" setup>
import { Badge, Card, Button } from "frappe-ui";

interface MembershipType {
  name: string;
  membership_type: string;
  amount: number;
  benefits: string[];
}

defineProps<{
  membershipType: MembershipType;
}>();
</script>
