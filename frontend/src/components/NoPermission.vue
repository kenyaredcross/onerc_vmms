<template>
	<div
		class="flex flex-col items-center justify-center py-20 h-[75vh] bg-surface-gray-50 m-8 md:m-16 text-center md:px-4"
	>
		<div class="bg-red-100 rounded-full p-6 mb-6 shadow-md">
			<LogIn class="w-12 h-12 text-red-600" />
		</div>

		<h2 class="text-4xl-black md:text-5xl text-ink-gray-1-900 mb-4">
			{{ __("Authentication Required") }}
		</h2>

		<p class="text-ink-gray-1-600 mb-8 max-w-md">
			{{ __("Please log in to access your") }} {{ __(page) }}
			{{ __("and continue exploring our features.") }}
		</p>

		<div class="flex gap-4">
			<button
				type="button"
				class="bg-red-600 hover:bg-red-700 text-white px-8 py-3 flex items-center gap-3 rounded-xl shadow-lg cursor-pointer"
				@click="redirectToLogin"
			>
				<LogIn class="w-5 h-5" />
				{{ __("Login") }}
			</button>

			<button
				type="button"
				class="bg-surface-base border border-red-600 text-red-600 px-8 py-3 flex items-center gap-3 rounded-xl cursor-pointer hover:bg-red-50"
				@click="redirectToSignup"
			>
				<UserPlus class="w-5 h-5" />
				{{ __("Sign up") }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { goToLogin, goToSignup } from "@/utils/auth";
import { LogIn, UserPlus } from "lucide-vue-next";

function redirectToLogin() {
	goToLogin();
}

function redirectToSignup() {
	goToSignup();
}

defineProps({
	page: String,
});
</script>
