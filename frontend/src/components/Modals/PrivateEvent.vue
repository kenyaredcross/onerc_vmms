<template>
	<Dialog v-model="dialog">
		<template #body-title>
			<div class="flex items-center gap-2">
				<Lock class="w-5 h-5 text-red-600" />
				<h3 class="text-2xl-bold text-ink-gray-1-900">Exclusive Event</h3>
			</div>
		</template>

		<template #body-content>
			<div class="space-y-4">
				<p class="text-ink-gray-1-700">
					You've discovered an exclusive event! This is a
					<span class="font-semibold text-red-600">private event</span>
					available only to our registered members.
				</p>
				<div class="bg-red-50 border border-red-100 rounded-lg p-4">
					<p class="text-sm text-ink-gray-1-700">
						<span class="font-semibold text-ink-gray-1-900">Why sign in?</span><br />
						Access exclusive events, manage your registrations, and stay updated with
						personalized event recommendations.
					</p>
				</div>
				<p class="text-ink-gray-1-600 text-sm">
					Already have an account? Log in to view event details. New here? Create an
					account to unlock access.
				</p>
			</div>
		</template>

		<template #actions="{ close }">
			<div class="flex justify-end gap-2">
				<Button variant="outline" @click="close">Cancel</Button>
				<Button variant="solid" theme="blue" @click="redirect(true)"> Log In </Button>
				<Button variant="solid" theme="red" @click="redirect(false)"> Sign Up </Button>
			</div>
		</template>
	</Dialog>
</template>
<script lang="ts" setup>
import { Dialog, Button } from "frappe-ui";
import { goToLogin, goToSignup } from "@/utils/auth";
import { Lock } from "lucide-vue-next";
import { ref } from "vue";

const dialog = ref(false);

function redirect(login: boolean) {
	if (login) {
		goToLogin();
	} else {
		goToSignup();
	}
}
</script>
