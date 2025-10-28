<template>
  <div
    class="relative flex flex-col w-full max-w-sm mx-auto rounded-3xl p-8 sm:p-6 xs:p-5 bg-white shadow-lg hover:shadow-2xl transition-all duration-700 group border border-gray-100 overflow-hidden hover:border-red-100 hover:-translate-y-1"
  >
    <div class="mb-6 text-center">
      <h3
        class="text-2xl sm:text-xl font-bold text-gray-900 mb-2 tracking-tight"
      >
        {{ membershipType.membership_type }}
      </h3>
    </div>

    <div class="mb-6 text-center">
      <div class="flex items-baseline justify-center gap-1.5 sm:gap-1">
        <span
          class="text-4xl sm:text-3xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
        >
          KES {{ membershipType.amount }}
        </span>
        <span class="text-base sm:text-sm font-semibold text-gray-500"
          >/year</span
        >
      </div>
    </div>

    <div class="flex-1 mb-6">
      <div class="space-y-2.5 sm:space-y-2">
        <div>
          <h4 class="text-lg sm:text-base font-bold text-red-600 mb-1.5">
            What's included
          </h4>
        </div>
        <div
          v-for="benefit in membershipType.benefits"
          :key="benefit"
          class="flex items-center gap-2.5 sm:gap-2"
        >
          <div
            class="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5 text-red-600 bg-red-50"
          >
            <Check class="w-3.5 h-3.5" />
          </div>
          <span
            class="text-sm sm:text-xs font-medium text-gray-700 leading-snug"
          >
            {{ benefit }}
          </span>
        </div>
      </div>
    </div>

    <Button
      variant="solid"
      class="w-full py-3 sm:py-2.5 font-bold rounded-xl transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] shadow-lg border-0 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white hover:shadow-red-300/50"
    >
      <span class="flex items-center justify-center gap-2">
        Select Plan
        <ArrowRight class="w-4 h-4" />
      </span>
    </Button>
  </div>
</template>

<script lang="ts" setup>
import { Button } from "frappe-ui";
import { Check, ArrowRight } from "lucide-vue-next";

interface MembershipType {
  name: string;
  membership_type: string;
  amount: number;
  benefits: string[];
}

const props = defineProps<{
  membershipType: MembershipType;
}>();
</script>
