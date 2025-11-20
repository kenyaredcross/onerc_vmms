<template>
	<div
		class="bg-white rounded-lg shadow-md p-6 flex items-center space-x-4 hover:shadow-lg transition-shadow duration-200"
	>
		<div :class="['p-3 rounded-full', color]">
			<component :is="iconSvg" class="w-6 h-6 text-white" />
		</div>
		<div>
			<div class="text-2xl font-bold text-gray-800">{{ value }}</div>
			<div class="text-sm text-gray-600">{{ label }}</div>
		</div>
	</div>
</template>

<script>
export default {
	name: "StatCard",
	props: {
		icon: {
			type: String,
			required: true,
			validator: (value) => ["star", "users", "trending-up", "calendar"].includes(value),
		},
		value: {
			type: [String, Number],
			required: true,
		},
		label: {
			type: String,
			required: true,
		},
		color: {
			type: String,
			default: "bg-blue-500",
		},
	},
	computed: {
		iconSvg() {
			const icons = {
				star: {
					template: `
						<svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
							<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
						</svg>
					`,
				},
				users: {
					template: `
						<svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
							<path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
						</svg>
					`,
				},
				"trending-up": {
					template: `
						<svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
							<path fill-rule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clip-rule="evenodd" />
						</svg>
					`,
				},
				calendar: {
					template: `
						<svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
							<path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd" />
						</svg>
					`,
				},
			};

			return (
				icons[this.icon] || {
					template: `<svg fill="currentColor" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" /></svg>`,
				}
			);
		},
	},
};
</script>
