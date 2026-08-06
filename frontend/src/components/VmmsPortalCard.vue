<template>
	<div
		class="relative flex flex-col w-full max-w-sm mx-auto rounded-2xl bg-surface-base border border-outline-gray-2 hover:shadow-xl transition-all duration-500 hover:-translate-y-1 overflow-hidden group"
	>
		<!-- Top accent bar -->
		<div
			class="h-1 w-full bg-gradient-to-r from-surface-red-4 via-surface-red-7 to-surface-red-8"
		/>

		<!-- Header -->
		<div class="px-5 pt-5 pb-5">
			<h3 class="text-2xl-bold text-ink-gray-9 tracking-tight">
				{{ __(membershipType.membership_type) }}
			</h3>
		</div>

		<!-- Divider -->
		<div class="mx-7 border-t border-outline-gray-1" />

		<!-- Pricing -->
		<div class="px-7 py-5">
			<div class="flex items-end gap-1">
				<span class="text-4xl-black text-ink-gray-9 leading-none">
					{{ __("KES") }} {{ __(membershipType.amount) }}
				</span>
				<span v-if="priceSuffix" class="text-base-semibold sm:text-sm text-gray-500">{{
					priceSuffix
				}}</span>
			</div>
			<p v-if="billingNote" class="mt-1.5 text-xs-medium text-gray-500">
				{{ billingNote }}
			</p>
		</div>

		<!-- Benefits -->
		<div class="px-7 pb-5 flex-1">
			<p class="text-xs-semibold text-ink-red-8 uppercase tracking-widest mb-3">
				{{ __("What's included") }}
			</p>
			<ul class="space-y-2.5">
				<li
					v-for="benefit in membershipType.benefits"
					:key="benefit"
					class="flex items-start gap-3"
				>
					<span
						class="mt-0.5 flex-shrink-0 w-4 h-4 rounded-full bg-surface-red-1 flex items-center justify-center"
					>
						<Check class="w-2.5 h-2.5 text-ink-red-6" />
					</span>
					<span class="text-sm text-ink-gray-6 leading-snug">
						{{ __(benefit.benefit) }}
					</span>
				</li>
			</ul>
		</div>

		<!-- Age Requirement -->
		<div
			v-if="membershipType.requires_age_requirement"
			class="mx-7 mb-5 flex items-center gap-2 rounded-lg bg-surface-gray-1 px-3.5 py-2.5"
		>
			<span class="text-xs leading-snug">
				<template v-if="membershipType.lower_age_limit === 0">
					{{ __("Open to ages below") }}
					<strong class="text-ink-gray-8"
						>{{ membershipType.upper_age_limit }} {{ __("yrs") }}</strong
					>
				</template>
				<template v-else-if="membershipType.lower_age_limit >= 30">
					{{ __("Open to ages") }}
					<strong class="text-ink-gray-8">{{ __("30 yrs and above") }}</strong>
				</template>
				<template v-else>
					{{ __("Open to ages") }}
					<strong class="text-ink-gray-8">
						{{ membershipType.lower_age_limit }}–{{ membershipType.upper_age_limit }}
						{{ __("yrs") }}
					</strong>
				</template>
			</span>
		</div>

		<!-- CTA -->
		<div class="px-7 pb-7">
			<Button
				variant="solid"
				theme="red"
				class="w-full py-2.5 rounded-xl text-sm-semibold transition-all duration-200 active:scale-[0.98]"
			>
				<span class="flex items-center justify-center gap-2">
					{{ __("Select Plan") }}
					<ArrowRight class="w-4 h-4" />
				</span>
			</Button>
		</div>
	</div>
</template>
<script setup>
import { Button } from "frappe-ui";
import { ArrowRight, Check } from "lucide-vue-next";
import { computed } from "vue";

const props = defineProps({
	membershipType: Object,
});

const priceSuffix = computed(() => {
	if (props.membershipType?.billing_cycle === "Monthly") return __("/month");
	if (props.membershipType?.billing_cycle === "One Off") return "";
	return __("/year");
});

const billingNote = computed(() => {
	if (props.membershipType?.billing_cycle !== "One Off") return "";
	return __("One-off payment — lifetime membership, no renewals");
});
</script>
