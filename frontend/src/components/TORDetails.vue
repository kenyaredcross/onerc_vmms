<template>
	<div
		v-if="termDetails"
		class="bg-white text-gray-900 p-10 rounded-2xl shadow-lg max-w-6xl mx-auto print:max-w-full print:shadow-none print:p-0 font-sans"
	>
		<header class="border-b-4 border-red-700 pb-6 mb-10 flex items-center justify-between">
			<div>
				<h1 class="text-3xl font-extrabold text-red-700 uppercase tracking-wide">
					Terms of Reference
				</h1>
				<p class="text-sm text-gray-600 mt-1">
					Reference No: <span class="font-semibold">{{ termDetails.name }}</span>
				</p>
			</div>
		</header>

		<section class="mb-10">
			<h2 class="section-title">Mission Details</h2>
			<div class="grid grid-cols-2 gap-6 text-[15px]">
				<p>
					<span class="label">Title of Mission:</span> {{ termDetails.title_of_mission }}
				</p>
				<p><span class="label">Region / Branch:</span> {{ termDetails.company }}</p>
				<p>
					<span class="label">Expected Start Date:</span>
					{{ formatDate(termDetails.expected_start_date) }}
				</p>
				<p>
					<span class="label">Expected End Date:</span>
					{{ formatDate(termDetails.expected_end_date) }}
				</p>
			</div>
		</section>

		<section class="mb-10">
			<h2 class="section-title">Mission Background</h2>
			<div
				class="prose prose-red max-w-none text-[15px] leading-relaxed"
				v-html="termDetails.mission_background"
			></div>
		</section>

		<section v-if="termDetails.stakeholders?.length" class="mb-10">
			<h2 class="section-title">Stakeholders</h2>
			<div class="table-container">
				<table class="styled-table">
					<thead>
						<tr>
							<th>Designation</th>
							<th>Name</th>
							<th>Phone Number</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(row, i) in termDetails.stakeholders" :key="i">
							<td>{{ row.designation }}</td>
							<td>{{ row.full_name }}</td>
							<td>{{ row.phone_number }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<section v-if="termDetails.objectives?.length" class="mb-10">
			<h2 class="section-title">Specific Objectives</h2>
			<ol class="list-decimal ml-6 space-y-2 text-[15px]">
				<li v-for="(row, i) in termDetails.objectives" :key="i">
					{{ row.objective }}
				</li>
			</ol>
		</section>

		<section v-if="termDetails.expected_outputs?.length" class="mb-10">
			<h2 class="section-title">Expected Outputs</h2>
			<ol class="list-decimal ml-6 space-y-2 text-[15px]">
				<li v-for="(row, i) in termDetails.expected_outputs" :key="i">
					{{ row.output }}
				</li>
			</ol>
		</section>

		<section v-if="termDetails.approach_methods?.length" class="mb-10">
			<h2 class="section-title">Proposed Approach</h2>
			<div class="table-container">
				<table class="styled-table">
					<thead>
						<tr>
							<th>Methodology</th>
							<th>Notes</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(row, i) in termDetails.approach_methods" :key="i">
							<td>{{ row.methodology }}</td>
							<td>{{ row.notes }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<section v-if="termDetails.itinerary?.length" class="mb-10">
			<h2 class="section-title">Itinerary</h2>
			<div class="table-container">
				<table class="styled-table">
					<thead>
						<tr>
							<th>Date</th>
							<th>Time</th>
							<th>Person Responsible</th>
							<th>Activity</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(row, i) in termDetails.itinerary" :key="i">
							<td>{{ formatDate(row.date) }}</td>
							<td>{{ row.time }}</td>
							<td>{{ row.person_responsible }}</td>
							<td>{{ row.activity }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<section v-if="termDetails.resources?.length" class="mb-10">
			<h2 class="section-title">Resources</h2>
			<div class="table-container">
				<table class="styled-table">
					<thead>
						<tr>
							<th>Date</th>
							<th>Resource</th>
							<th>Donor</th>
							<th>Project Code</th>
							<th class="text-right">Quantity</th>
							<th class="text-right">Unit</th>
							<th class="text-right">Unit Cost</th>
							<th class="text-right">Total Cost</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(row, i) in termDetails.resources" :key="i">
							<td>{{ formatDate(row.date) }}</td>
							<td>{{ row.resource }}</td>
							<td>{{ row.donor }}</td>
							<td>{{ row.project_code }}</td>
							<td class="text-right">{{ row.quantity }}</td>
							<td class="text-right">{{ row.unit }}</td>
							<td class="text-right">{{ formatCurrency(row.cost_per_day) }}</td>
							<td class="text-right">{{ formatCurrency(row.total_cost) }}</td>
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

<style scoped>
.section-title {
	@apply text-xl font-bold text-red-700 border-b-2 border-red-700 mb-4 pb-1 uppercase tracking-wide;
}
.label {
	@apply font-semibold text-gray-800;
}
.table-container {
	@apply overflow-x-auto rounded-lg shadow-sm border border-gray-200;
}
.styled-table {
	@apply w-full text-sm border-collapse;
}
.styled-table th {
	@apply bg-red-700 text-white font-semibold p-2 border border-red-700 text-left;
}
.styled-table td {
	@apply border border-gray-200 p-2;
}
.styled-table tr:nth-child(even) td {
	@apply bg-gray-50;
}
.prose-red :where(h1, h2, h3, h4) {
	color: #b71c1c !important;
}
@media print {
	* {
		color-adjust: exact !important;
		-webkit-print-color-adjust: exact !important;
	}
	header img {
		filter: grayscale(0) !important;
	}
	table,
	th,
	td {
		border: 1px solid #999 !important;
	}
}
</style>
