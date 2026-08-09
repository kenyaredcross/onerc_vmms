<template>
	<div class="flex items-center justify-center min-h-screen">
		<div class="flex flex-col justify-center items-center text-center text-ink-red-8">
			<Spinner class="w-12" />
			<p class="text-ink-gray-6">{{ __("Loading deployment details...") }}</p>
		</div>
	</div>
</template>

<script setup>
import { Spinner } from "frappe-ui";
</script>
