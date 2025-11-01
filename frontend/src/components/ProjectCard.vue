<template>
	<div
		class="flex flex-col border border-gray-200 rounded-lg p-4 h-full hover:border-gray-300 hover:shadow-sm transition-all duration-200 bg-white"
	>
		<div class="flex flex-col space-y-3 mb-4 flex-1">
			<div class="text-lg font-semibold text-gray-900 leading-tight">
				{{ __(project.project_name) }}
			</div>

			<span class="font-medium text-gray-700 leading-5 text-sm">
				{{ __(project.project_type) }}
			</span>

			<div class="flex items-center space-x-2 text-sm">
				<Calendar class="w-3 h-3 flex-shrink-0" />
				<span>{{ __("Start") }}</span>
				<span>{{ __(project.expected_start_date) }}</span>
			</div>

			<div class="flex items-center space-x-2 text-sm">
				<Clock class="w-3 h-3 flex-shrink-0" />
				<span>{{ __("End") }}</span>
				<span>{{ __(project.expected_end_date) }}</span>
			</div>
		</div>

		<div class="flex flex-wrap gap-2 mt-auto pt-3 border-t border-gray-100">
			<Badge>
				{{ __(project.status) }}
			</Badge>
			<Badge> {{ __("Priority:") }} {{ __(project.priority) }} </Badge>
			<Badge>
				{{ __(project.is_active ? "Active" : "Inactive") }}
			</Badge>
		</div>

		<Button
			variant="solid"
			theme="gray"
			size="sm"
			:label="__('View')"
			class="m-3"
			@click="showDialog = true"
		/>
	</div>

	<Dialog v-model="showDialog">
		<template #body-title>
			<h3 class="text-2xl font-semibold text-ink-gray-9">
				{{ __("Project:") }} {{ __(project.project_name) }}
			</h3>
		</template>
		<template #body-content>
			<div class="space-y-2">
				<p>
					<strong>{{ __("Status:") }}</strong> {{ __(project.status) }}
				</p>
				<p>
					<strong>{{ __("Type:") }}</strong> {{ __(project.project_type) }}
				</p>
				<p>
					<strong>{{ __("Priority:") }}</strong
					><Badge :theme="getProjectSeverity(project.priority)" size="lg">
						{{ __(project.priority) }}</Badge
					>
				</p>
				<p>
					<strong>{{ __("Progress:") }}</strong> {{ __(project.percent_complete)
					}}{{ __("%") }}
				</p>
				<p>
					<strong>{{ __("Start Date:") }}</strong> {{ __(project.expected_start_date) }}
				</p>
				<p>
					<strong>{{ __("End Date:") }}</strong> {{ __(project.expected_end_date) }}
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-between space-x-2">
				<Button size="lg" variant="solid" color="green" @click="acceptProject">
					{{ __("Accept") }}
				</Button>
				<Button size="lg" variant="solid" theme="red" @click="rejectProject">
					{{ __("Reject") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script lang="ts" setup>
import { Badge, Button, Dialog } from "frappe-ui";
import { Calendar, Clock } from "lucide-vue-next";
import { ref } from "vue";

export interface Project {
	name: string;
	project_name: string;
	status: string;
	project_type: string;
	is_active: number;
	percent_complete: number;
	priority: string;
	expected_start_date: string;
	expected_end_date: string;
}

const props = defineProps<{
	project: Project;
}>();

const showDialog = ref(false);

const acceptProject = () => {
	showDialog.value = false;
};

const rejectProject = () => {
	showDialog.value = false;
};

function getProjectSeverity(
	priority: string,
): "gray" | "blue" | "green" | "red" | "orange" | undefined {
	switch (priority.toLowerCase()) {
		case "high":
			return "red";
		case "medium":
			return "orange";
		case "low":
			return "green";
		default:
			return "gray";
	}
}
</script>
