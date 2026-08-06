<template>
	<div v-if="membershipTypes.data?.length > 0" class="flex justify-center mt-10">
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
	<EmptyState v-else :type="__('Membership Types')" />

	<div class="t py-16">
		<div class="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between px-6">
			<div>
				<h2 class="text-4xl-bold md:text-5xl m-2">
					{{ __("Sign up to be a volunteer today!") }}
				</h2>
				<router-link :to="{ name: 'Login', hash: '#signup' }">
					<Button
						:variant="'solid'"
						:ref_for="true"
						theme="gray"
						size="lg"
						:label="__('Button')"
						:loading="false"
						:disabled="false"
						:tooltip="__('Hover for more!')"
					>
						{{ __("Sign up") }}
					</Button>
				</router-link>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { Button } from "frappe-ui";
import { RouterLink } from "vue-router";
import EmptyState from "../components/EmptyState.vue";
import VmmsPortalCard from "../components/VmmsPortalCard.vue";
import { membershipStore } from "../stores/membership";

const { membershipTypes } = membershipStore();

useHead({
	title: "Join the Kenya Red Cross | Membership & Volunteer Sign Up",
	meta: [
		{
			name: "description",
			content:
				"Discover membership and volunteer opportunities with the Kenya Red Cross. View available membership plans and sign up to start contributing today.",
		},
	],
});
</script>
