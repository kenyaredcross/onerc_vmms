<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-4 py-3 sm:px-6"
		>
			<Breadcrumbs
				class="h-7"
				:items="[
					{ label: __('Jobs'), route: { name: 'Jobs' } },
					{
						label: job.data?.job_title,
						route: { name: 'JobDetail', params: { job: job.data?.name } },
					},
				]"
			/>
		</header>

		<div v-if="job.data" class="mx-auto px-4 sm:px-6 pt-6">
			<JobDetails :job="job" />
		</div>
	</div>
</template>

<script setup>
import { Breadcrumbs, createResource, usePageMeta } from "frappe-ui";
import { computed, inject } from "vue";
import { useRouter } from "vue-router";
import JobDetails from "../components/JobDetails.vue";
import { sessionStore } from "../stores/session";

const router = useRouter();
const user = inject("$user");
const dayjs = inject("$dayjs");
const { brand } = sessionStore();
const props = defineProps({
	job: {
		type: String,
		required: true,
	},
});

const job = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.get_job_details",
	params: { job: props.job },
	cache: ["job", props.job],
	auto: true,
});

const jobApplication = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.doc.get_list",
	makeParams() {
		return {
			doctype: "Job Applicant",
			filters: {
				job_title: props.job,
				email_id: user.data?.email,
			},
			fields: ["name"],
		};
	},
	auto: true,
	reloadOn: () => !!user.data?.email,
});

const isApplied = computed(() => jobApplication.data?.length > 0);
const applicationId = computed(() => jobApplication.data?.[0]?.name || null);

const redirectToLogin = () => {
	const currentPath = router.currentRoute.value.fullPath;
	router.push({
		name: "Login",
		query: { "redirect-to": currentPath },
	});
};

const goToNewApplication = () => {
	router.push({
		name: "NewJobApplication",
	});
};

const goToApplicationDetail = () => {
	if (applicationId.value) {
		router.push({
			name: "JobApplicationDetail",
			params: { id: applicationId.value },
		});
	}
};

const redirectToWebsite = (url) => {
	window.open(url, "_blank");
};

const getCompanyAbbr = (name) =>
	name
		? name
				.split(" ")
				.map((word) => word[0])
				.join("")
				.slice(0, 2)
				.toUpperCase()
		: "NA";

usePageMeta(() => ({
	title: job.data?.job_title,
	icon: brand.favicon,
}));
</script>
