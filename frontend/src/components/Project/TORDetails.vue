<template>
	<div
		v-if="termDetails"
		class="bg-surface-white text-ink-gray-1-900 p-4 sm:p-6 lg:p-10 rounded-2xl shadow-lg max-w-full sm:max-w-6xl mx-auto print:max-w-full print:shadow-none print:p-0 font-sans break-words"
	>
		<header
			class="border-b-4 border-red-700 pb-6 mb-8 sm:mb-10 flex flex-col sm:flex-row items-start sm:items-center justify-between"
		>
			<div class="w-full">
				<h1
					class="text-2xl sm:text-3xl font-extrabold text-red-700 uppercase tracking-wide"
				>
					Terms of Reference
				</h1>
				<p class="text-xs sm:text-sm text-ink-gray-1-600 mt-1">
					Reference No: <span class="font-semibold">{{ termDetails.name }}</span>
				</p>
			</div>
		</header>

		<section class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Mission Details
			</h2>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 text-[15px]">
				<p>
					<span class="font-semibold text-ink-gray-1-800">Title of Mission:</span>
					{{ termDetails.title_of_mission }}
				</p>
				<p>
					<span class="font-semibold text-ink-gray-1-800">Region / Branch:</span>
					{{ termDetails.company }}
				</p>
				<p>
					<span class="font-semibold text-ink-gray-1-800">Expected Start Date:</span>
					{{ formatDate(termDetails.expected_start_date) }}
				</p>
				<p>
					<span class="font-semibold text-ink-gray-1-800">Expected End Date:</span>
					{{ formatDate(termDetails.expected_end_date) }}
				</p>
			</div>
		</section>

		<section class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Mission Background
			</h2>
			<div
				class="prose prose-red max-w-none text-[15px] leading-relaxed [&_h1]:!text-red-700 [&_h2]:!text-red-700 [&_h3]:!text-red-700"
				v-html="termDetails.mission_background"
			></div>
		</section>

		<section v-if="termDetails.stakeholders?.length" class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Stakeholders
			</h2>
			<div class="overflow-x-auto rounded-lg shadow-sm border border-outline-gray-200">
				<table class="w-full text-sm border-collapse table-auto">
					<thead>
						<tr>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Designation
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Name
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Phone Number
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(row, i) in termDetails.stakeholders"
							:key="i"
							:class="{ 'bg-surface-gray-50': (i + 1) % 2 === 0 }"
						>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.designation }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.full_name }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.phone_number }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<section v-if="termDetails.objectives?.length" class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Specific Objectives
			</h2>
			<ol class="list-decimal ml-6 space-y-2 text-[15px]">
				<li v-for="(row, i) in termDetails.objectives" :key="i">
					{{ row.objective }}
				</li>
			</ol>
		</section>

		<section v-if="termDetails.expected_outputs?.length" class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Expected Outputs
			</h2>
			<ol class="list-decimal ml-6 space-y-2 text-[15px]">
				<li v-for="(row, i) in termDetails.expected_outputs" :key="i">
					{{ row.output }}
				</li>
			</ol>
		</section>

		<section v-if="termDetails.approach_methods?.length" class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Proposed Approach
			</h2>
			<div class="overflow-x-auto rounded-lg shadow-sm border border-outline-gray-200">
				<table class="w-full text-sm border-collapse table-auto">
					<thead>
						<tr>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Methodology
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Notes
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(row, i) in termDetails.approach_methods"
							:key="i"
							:class="{ 'bg-surface-gray-50': (i + 1) % 2 === 0 }"
						>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.methodology }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.notes }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<section v-if="termDetails.itinerary?.length" class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Itinerary
			</h2>
			<div class="overflow-x-auto rounded-lg shadow-sm border border-outline-gray-200">
				<table class="w-full text-sm border-collapse table-auto">
					<thead>
						<tr>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Date
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Time
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Person Responsible
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Activity
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(row, i) in termDetails.itinerary"
							:key="i"
							:class="{ 'bg-surface-gray-50': (i + 1) % 2 === 0 }"
						>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ formatDate(row.date) }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.time }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.person_responsible }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.activity }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<section v-if="termDetails.resources?.length" class="mb-8 sm:mb-10">
			<h2
				class="text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide"
			>
				Resources
			</h2>
			<div class="overflow-x-auto rounded-lg shadow-sm border border-outline-gray-200">
				<table class="w-full text-sm border-collapse table-auto">
					<thead>
						<tr>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Date
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Resource
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Donor
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-left whitespace-nowrap"
							>
								Project Code
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-right whitespace-nowrap"
							>
								Quantity
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-right whitespace-nowrap"
							>
								Unit
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-right whitespace-nowrap"
							>
								Unit Cost
							</th>
							<th
								class="bg-red-700 text-white font-semibold p-2 border border-red-700 text-right whitespace-nowrap"
							>
								Total Cost
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(row, i) in termDetails.resources"
							:key="i"
							:class="{ 'bg-surface-gray-50': (i + 1) % 2 === 0 }"
						>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ formatDate(row.date) }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.resource }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.donor }}
							</td>
							<td class="border border-outline-gray-200 p-2 break-words">
								{{ row.project }}
							</td>
							<td class="border border-outline-gray-200 p-2 text-right break-words">
								{{ row.quantity }}
							</td>
							<td class="border border-outline-gray-200 p-2 text-right break-words">
								{{ row.unit }}
							</td>
							<td class="border border-outline-gray-200 p-2 text-right break-words">
								{{ formatCurrency(row.cost_per_day) }}
							</td>
							<td class="border border-outline-gray-200 p-2 text-right break-words">
								{{ formatCurrency(row.total_cost) }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<div class="mt-6 text-center">
			<div class="flex justify-center">
				<a
					:href="torUrl ? torUrl : null"
					:target="torUrl ? '_blank' : null"
					rel="noopener noreferrer"
					role="button"
					:aria-disabled="!torUrl"
					:class="[
						'flex-1 text-center px-6 py-3 rounded-lg font-semibold transition-colors',
						torUrl
							? 'bg-green-600 hover:bg-green-700 text-white'
							: 'bg-green-600/40 text-white pointer-events-none opacity-60 cursor-not-allowed',
					]"
				>
					{{ __("Download TOR") }}
				</a>
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	termDetails: {
		type: Object,
		required: true,
	},
	torUrl: {
		type: String,
		required: false,
	},
});

const formatDate = (date) => {
	if (!date) return "";
	return new Date(date).toLocaleDateString(undefined, {
		year: "numeric",
		month: "short",
		day: "numeric",
	});
};

const formatCurrency = (val) => {
	if (val == null || val === "") return "";
	return new Intl.NumberFormat(undefined, {
		style: "currency",
		currency: "KES",
	}).format(val);
};
</script>
