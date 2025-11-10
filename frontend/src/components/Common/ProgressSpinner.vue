<template>
	<div class="flex flex-col justify-center items-center my-auto text-center text-3xl">
		<LoaderCircle class="animate-spin text-red-500" style="width: 64px; height: 64px" />
		<span class="text-base"> {{ __(message) }}</span>
	</div>
</template>
<script setup>
import { LoaderCircle } from "lucide-vue-next";

const props = defineProps({
	message: String,
});
</script>
