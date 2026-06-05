<template>
	<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
		<h2 class="text-lg font-semibold text-gray-900 mb-4">
			{{ __("Project Information") }}
		</h2>
		<div class="space-y-4">
			<div>
				<label class="text-sm font-medium text-gray-600">{{ __("Status") }}</label>
				<p class="text-sm text-gray-900 mt-1 flex items-center gap-2">
					<span
						class="w-2 h-2 rounded-full"
						:class="getStatusColor(project.project.status)"
					></span>
					{{ project.project.status }}
				</p>
			</div>
			<div>
				<label class="text-sm font-medium text-gray-600">{{ __("Active") }}</label>
				<p class="text-sm text-gray-900 mt-1">
					{{ project.project.is_active }}
				</p>
			</div>
			<div>
				<label class="text-sm font-medium text-gray-600">{{ __("Location") }}</label>
				<p class="text-sm text-gray-900 mt-1">
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
		Open: "bg-blue-500",
		Working: "bg-orange-500",
		Completed: "bg-green-500",
		Cancelled: "bg-red-500",
		"On Hold": "bg-yellow-500",
	};
	return colorMap[status] || "bg-gray-500";
};
</script>
