<template>
	<div></div>

	<Availability
		@success="updateAvailability"
		v-model="setAvailability"
		@cancel="updateAvailability"
	/>
</template>

<script setup>
import { ref } from "vue";
import { usersStore } from "../stores/user";
import Availability from "./Modals/Availability.vue";

const setAvailability = ref(false);
const { presentSlots } = usersStore();

function updateAvailability() {
	presentSlots.reload();
	setAvailability.value = false;
}
</script>
