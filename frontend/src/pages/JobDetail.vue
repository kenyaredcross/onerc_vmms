<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-base px-4 py-3 md:px-6"
		>
			<Breadcrumbs
				class="h-7"
				:items="[
					{ label: __('Opportunities'), route: { name: 'Jobs' } },
					{
						label: __(job.data?.job_title),
						route: { name: 'JobDetail', params: { job: job.data?.name } },
					},
				]"
			/>
		</header>

		<div v-if="job.data" class="px-4 md:px-6 pt-6">
			<JobDetails :job="job" />
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { Breadcrumbs, createResource, usePageMeta } from "frappe-ui";
import { computed } from "vue";
import JobDetails from "../components/JobDetails.vue";
import { sessionStore } from "../stores/session";

const { brand } = sessionStore();
const props = defineProps({
	job: {
		required: true,
	},
});

const job = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.get_job_details",
	params: { job: props.job },
	cache: ["job", props.job],
	auto: true,
});

usePageMeta(() => ({
	title: job.data?.job_title,
	icon: brand.favicon,
}));

useHead({
	title: computed(() =>
		job.data?.job_title
			? `${job.data.job_title} | Opportunity Details - Kenya Red Cross`
			: "Opportunity Details | Kenya Red Cross VMMS"
	),
	meta: [
		{
			name: "description",
			content: computed(() =>
				job.data?.job_description
					? `Job Description for ${
							job.data.job_title
					  }: ${job.data.job_description.substring(
							0,
							150
					  )}... Apply now at the Kenya Red Cross.`
					: "View the full job description, requirements, and application process for this opportunity with the Kenya Red Cross."
			),
		},
	],
});
</script>
