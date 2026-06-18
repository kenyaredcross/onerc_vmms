<template>
	<div class="min-h-screen bg-gray-50">
		<ProjectLoading v-if="DeploymentDetail.loading" />
		<ProjectError v-else-if="DeploymentDetail.error" @reload="DeploymentDetail.reload()" />
		<ProjectContent
			v-else-if="DeploymentDetail.data"
			:project="DeploymentDetail.data"
			@accept="acceptAssignment"
			@reject="rejectAssignment"
			@download-contract="downloadContract"
		/>
	</div>
</template>

<script setup>
import ProjectContent from "@/components/Project/ProjectContent.vue";
import ProjectError from "@/components/Project/ProjectError.vue";
import ProjectLoading from "@/components/Project/ProjectLoading.vue";
import { useHead } from "@vueuse/head";
import { createResource, toast } from "frappe-ui";
import { computed, inject, onMounted } from "vue";
import { useRoute } from "vue-router";
import router from "../router";

const route = useRoute();
const user = inject("$user");

onMounted(() => {
	if (!user.data) {
		toast.warning("You must be logged in to view this page");
		setTimeout(() => {
			router.push("/login");
		}, 500);
	}
});

const projectParams = computed(() => {
	return route.params.id;
});

const DeploymentDetail = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.projects.get_assignment_details",
	auto: true,
	cache: ["project_detail", projectParams.value],
	makeParams() {
		return { assignment_name: projectParams.value };
	},
});

const acceptAssignment = (deploymentAssignment, contractName) => {
	assignmentDecision.submit({
		name: deploymentAssignment,
		accepted: true,
		contract_name: contractName,
	});
};

const rejectAssignment = (deploymentAssignment) => {
	assignmentDecision.submit({ name: deploymentAssignment, accepted: false });
};

const assignmentDecision = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.projects.accept_assignment",
	makeParams(values) {
		return values;
	},
	onSuccess() {
		toast.success("Your decision has been recorded.");
		DeploymentDetail.reload();
	},
});

const downloadContract = (contractName) => {
	loading.value = true;

	let headers = { "X-Frappe-Site-Name": window.location.hostname };
	if (window.csrf_token) {
		headers["X-Frappe-CSRF-Token"] = window.csrf_token;
	}

	fetch("/api/method/frappe.utils.print_format.download_pdf", {
		method: "POST",
		headers,
		body: new URLSearchParams({
			doctype: "Contract",
			name: contractName,
		}),
	})
		.then((response) => {
			if (response.ok) {
				return response.blob();
			} else {
				downloadError.value = "Failed to download PDF";
			}
		})
		.then((blob) => {
			if (!blob) return;
			const blobUrl = window.URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = blobUrl;
			link.download = `${contractName}.pdf`;
			link.click();

			setTimeout(() => {
				window.URL.revokeObjectURL(blobUrl);
			}, 3000);
		})
		.catch((error) => {
			downloadError.value = `Failed to download PDF: ${error.message}`;
		})
		.finally(() => {
			loading.value = false;
		});
};

useHead({
	title: "Project Assignment Details | Gambia Red Cross Society",
	meta: [
		{
			name: "description",
			content:
				"View details for your assigned Gambia Red Cross Society project, including progress, timeline, and assignment decision (Accept/Reject).",
		},
	],
});
</script>
