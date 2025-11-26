<template>
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<StatCard
			icon="star"
			:value="stats.energyPoints"
			label="Energy Points"
			color="bg-purple-500"
		/>
		<StatCard
			icon="users"
			:value="stats.reviewPoints"
			label="Review Points"
			color="bg-blue-500"
		/>
		<StatCard
			icon="trending-up"
			:value="`#${stats.rank}`"
			label="All-Time Rank"
			color="bg-teal-500"
		/>
		<StatCard
			icon="calendar"
			:value="`#${stats.monthRank}`"
			label="Monthly Rank"
			color="bg-pink-500"
		/>
	</div>
</template>

<script setup>
import StatCard from "./StatCard.vue";
const props = defineProps({
	stats: {
		type: Object,
		required: true,
	},
});
</script>
