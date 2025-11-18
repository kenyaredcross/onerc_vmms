<template>
	<div class="max-w-6xl mx-auto px-6 py-8">
		<ProjectHeader :project="project" />

		<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
			<div class="lg:col-span-2 space-y-6">
				<ProjectNotes :notes="project.project.notes" />
				<TORDetails :term-details="project?.term_details" :tor-url="project?.tor_url" />
			</div>

			<div class="space-y-6">
				<ProjectInfo :project="project" />

				<!-- NEW: Show Actions if project is submitted + accepted -->
				<ProjectActions
					v-if="project.docstatus === 1 && project.deployment_status === 'Accepted'"
					:project="project"
				/>

				<ContractAlert v-if="showContractAlert" :project="project" />

				<ProjectDecision
					v-if="project.deployment_status === 'Pending' && !showContractAlert"
					:project="project"
					@accept="handleAccept"
					@reject="$emit('reject', project.name)"
					@download-contract="$emit('download-contract', $event)"
				/>
			</div>
		</div>
	</div>

	<AcceptDialog
		v-model="acceptDialog"
		:loading="assignmentDecisionLoading"
		@confirm="handleConfirm"
	/>
</template>

<script setup>
import AcceptDialog from "@/components/Project/AcceptDialog.vue";
import ContractAlert from "@/components/Project/ContractAlert.vue";
import ProjectActions from "@/components/Project/ProjectActions.vue";
import ProjectDecision from "@/components/Project/ProjectDecision.vue";
import ProjectHeader from "@/components/Project/ProjectHeader.vue";
import ProjectInfo from "@/components/Project/ProjectInfo.vue";
import ProjectNotes from "@/components/Project/ProjectNotes.vue";
import TORDetails from "@/components/Project/TORDetails.vue";
import { computed, ref } from "vue";

const props = defineProps({
	project: {
		type: Object,
		required: true,
	},
});

const emit = defineEmits(["accept", "reject", "download-contract"]);

const acceptDialog = ref(false);
const assignmentDecisionLoading = ref(false);

const showContractAlert = computed(() => {
	return (
		props.project?.deployment_status === "Pending" &&
		props.project?.require_contract_before_deployment &&
		!props.project?.contract?.name
	);
});

const handleAccept = () => {
	acceptDialog.value = true;
};

const handleConfirm = () => {
	emit("accept", props.project.name, props.project.contract?.name);
	acceptDialog.value = false;
};
</script>
