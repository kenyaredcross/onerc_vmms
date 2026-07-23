<template>
	<div class="min-h-[70vh] flex flex-col items-center justify-center text-center px-4 py-16">
		<Compass class="w-16 h-16 text-red-700 mb-6" />

		<p class="text-6xl font-extrabold text-red-700 leading-none">404</p>
		<h1 class="mt-4 text-2xl font-bold text-ink-gray-9">
			{{ __("Page Not Found") }}
		</h1>
		<p class="mt-2 max-w-md text-ink-gray-6">
			{{ __("The page you are looking for doesn't exist or may have been moved.") }}
		</p>

		<div class="mt-8 flex flex-wrap items-center justify-center gap-3">
			<Button variant="subtle" @click="goBack">
				<template #prefix>
					<ArrowLeft class="w-4 h-4" />
				</template>
				{{ __("Go Back") }}
			</Button>
			<Button variant="solid" theme="red" @click="goHome">
				<template #prefix>
					<Home class="w-4 h-4" />
				</template>
				{{ __("Back to Dashboard") }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { Button } from "frappe-ui";
import { ArrowLeft, Compass, Home } from "lucide-vue-next";
import { useRouter } from "vue-router";

const router = useRouter();

function goHome() {
	router.push({ name: "Dashboard" });
}

function goBack() {
	if (window.history.state?.back) {
		router.back();
	} else {
		router.push({ name: "Dashboard" });
	}
}

useHead({
	title: "Page Not Found | Kenya Red Cross",
});
</script>
