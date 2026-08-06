<template>
	<div class="bg-surface-base rounded-xl border border-outline-gray-2 p-6">
		<h2 class="text-lg-semibold text-ink-gray-9 mb-4">
			{{ __("Project Information") }}
		</h2>
		<div class="space-y-4">
			<div>
				<label class="text-sm-medium text-ink-gray-6">{{ __("Status") }}</label>
				<p class="text-sm text-ink-gray-9 mt-1 flex items-center gap-2">
					<span
						class="w-2 h-2 rounded-full"
						:class="getStatusColor(project.project.status)"
					></span>
					{{ project.project.status }}
				</p>
			</div>
			<div>
				<label class="text-sm-medium text-ink-gray-6">{{ __("Active") }}</label>
				<p class="text-sm text-ink-gray-9 mt-1">
					{{ project.project.is_active }}
				</p>
			</div>
			<div>
				<label class="text-sm-medium text-ink-gray-6">{{ __("Location") }}</label>
				<p class="text-sm text-ink-gray-9 mt-1">
					{{ project.location }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup>
defineProps({
	project: {
		type: Object,
		required: true,
	},
});

const getStatusColor = (status) => {
	const colorMap = {
		Open: "bg-surface-blue-5",
		Working: "bg-surface-orange-5",
		Completed: "bg-surface-green-5",
		Cancelled: "bg-surface-red-5",
		"On Hold": "bg-surface-yellow-5",
	};
	return colorMap[status] || "bg-surface-gray-6";
};
</script>
