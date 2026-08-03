import { createResource, toast } from "frappe-ui";
import { computed, inject, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import router from "../router";

export function useAssignmentDetail() {
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

	const assignmentDecision = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.projects.accept_assignment",
		makeParams(values) {
			return values;
		},
		onSuccess() {
			toast.success("Your decision has been recorded.");
			DeploymentDetail.reload();
		},
		onError(err) {
			toast.error(err.messages?.[0] || err.message || "Could not record your decision.");
			DeploymentDetail.reload();
		},
	});

	const decisionError = computed(() => {
		const err = assignmentDecision.error;
		if (!err) return "";
		return err.messages?.[0] || err.message || "";
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

	const loading = ref(false);
	const downloadError = ref("");

	const downloadContract = (contractName) => {
		loading.value = true;
		downloadError.value = "";

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
					toast.error(downloadError.value);
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
				toast.error(downloadError.value);
			})
			.finally(() => {
				loading.value = false;
			});
	};

	return {
		DeploymentDetail,
		assignmentDecision,
		decisionError,
		loading,
		downloadError,
		acceptAssignment,
		rejectAssignment,
		downloadContract,
	};
}
