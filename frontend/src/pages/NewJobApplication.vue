<template>
	<div class="w-full space-y-8">
		<div v-if="!user.data?.name" class="bg-gray-50 rounded-xl p-6 border border-gray-200">
			<h3 class="text-xl font-semibold text-gray-800 mb-6">
				{{ __("Authentication Required") }}
			</h3>
			<p class="text-gray-600 mb-8 max-w-md">
				{{ __("Please create an account to submit your application") }}
			</p>

			<div
				variant="solid"
				class="bg-red-600 hover:bg-red-700 w-fit text-white px-8 py-3 flex items-center gap-3 rounded-xl shadow-lg cursor-pointer"
				@click="redirectToLogin"
			>
				<LogIn class="w-5 h-5" />
				{{ __("Sign Up") }}
			</div>
		</div>
		<div
			v-else-if="isApplied"
			class="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-center"
		>
			<h2 class="text-xl font-semibold text-yellow-800 mb-4">
				{{ __("You’ve already applied for this job.") }}
			</h2>
			<Button
				variant="solid"
				class="bg-red-700 hover:bg-red-800 text-white"
				@click="
					router.push({
						name: 'JobApplicationDetail',
						params: { id: applicationId },
					})
				"
			>
				{{ __("View Your Application") }}
			</Button>
		</div>

		<div
			v-else-if="
				job.data &&
				job.data.opportunity_type === 'Internal' &&
				user.data &&
				!user.data?.employee
			"
			class="bg-red-50 border border-red-200 rounded-xl p-6 text-center"
		>
			<h2 class="text-xl font-semibold text-red-800 mb-4">
				{{ __("This opportunity is available for volunteers only.") }}
			</h2>
			<Button
				variant="solid"
				class="bg-red-700 hover:bg-red-800 text-white"
				@click="router.push({ name: 'VolunteerSignup' })"
				v-if="!user.data?.is_pending_approval"
			>
				{{
					user.data.vol_applicant
						? __("Continue with Volunteer Registration")
						: __("Register Now")
				}}
			</Button>
			<div v-else class="text-gray-700">
				{{
					__(
						"Your application for volunteering is currently under review. Please come back later to apply for this opportunity.",
					)
				}}
			</div>
		</div>

		<div v-else class="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
			<h2 class="text-2xl font-bold text-red-700 mb-6">
				{{ __("Apply for this Opportunity") }}
			</h2>

			<form class="space-y-10" @submit.prevent="submitApplication">
				<div class="flex justify-start">
					<Button
						type="submit"
						variant="solid"
						class="bg-red-700 hover:bg-red-800 text-white px-6 py-3 rounded-lg"
					>
						{{ __("Start Application") }}
					</Button>
				</div>
			</form>
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { Button, createResource, toast } from "frappe-ui";
import { LogIn } from "lucide-vue-next";
import { computed, inject, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const user = inject("$user");
const jobId = route.params?.job || "";

const job = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.get_job_details",
	params: { job: jobId },
	onSuccess: (data) => {
		if (!data) {
			toast.error("Job not found");
			router.replace({ name: "JobListings" });
		}
	},
	cache: ["job", jobId],
	auto: true,
});

const form = ref({
	surname: "",
	other_names: "",
	email_id: "",
	phone: "",
	cover_letter: "",
});

const resume = ref(null);
const documents = ref([]);

const jobApplication = createResource({
	url: "frappe.client.get_list",
	makeParams() {
		return {
			doctype: "Job Applicant",
			filters: { job_title: jobId, email_id: user.data?.email },
			fields: ["name"],
		};
	},
	auto: true,
	reloadOn: () => !!user.data?.email,
});

const isApplied = computed(() => jobApplication.data?.length > 0);
const applicationId = computed(() => jobApplication.data?.[0]?.name || null);

const opportunityApplication = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.create_job_application",
	makeParams() {
		return {
			job_opening: jobId,
			...form.value,
			resume: resume.value,
			documents: documents.value,
		};
	},
});

const submitApplication = () => {
	opportunityApplication.submit(
		{},
		{
			onSuccess: (response) => {
				const applicationId = response?.name || response?.application_id;
				// toast.success("Application submitted successfully");
				router.push({
					name: "JobApplicationDetail",
					params: { id: applicationId },
				});
			},
			onError: (err) => toast.error(err.messages?.[0] || err),
		},
	);
};

function redirectToLogin() {
	router.push("/login#signup");
}

const redirectToWebsite = (url) => window.open(url, "_blank");
const getCompanyAbbr = (name) =>
	name
		? name
				.split(" ")
				.map((word) => word[0])
				.join("")
				.slice(0, 2)
				.toUpperCase()
		: "NA";

useHead({
	title: computed(() =>
		job.data?.job_title
			? `Start Application for ${job.data.job_title} | Tanzania Red Cross`
			: "Start Application | Tanzania Red Cross",
	),
	meta: [
		{
			name: "description",
			content: computed(() =>
				job.data?.job_title
					? `Ready to apply for ${job.data.job_title}? Log in or create an account to begin your application with the Tanzania Red Cross.`
					: "Access the application form to apply for this job or volunteer opportunity at the Tanzania Red Cross VMMS.",
			),
		},
	],
});
</script>
