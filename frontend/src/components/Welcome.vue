<template>
	<div
		v-if="!roleResource.data.is_pending_approval"
		class="h-[75vh] flex items-center justify-center"
	>
		<div class="max-w-6xl w-full grid grid-cols-1 md:grid-cols-2 gap-12 p-2 md:p-10">
			<div class="flex flex-col justify-center space-y-6 text-left">
				<h1 class="text-3xl md:text-6xl font-extrabold text-red-600 leading-tight">
					{{ __("Gambia Red Cross Society") }} <br />
				</h1>
				<p class="text-lg text-gray-700 max-w-lg">
					{{ __("Together, we can") }}
					<span class="font-semibold text-red-500">{{ __("save lives") }}</span
					>, {{ __("support") }}
					{{ __("communities, and make a") }}
					<span class="font-semibold text-red-500">{{ __("real difference") }}</span
					>. {{ __("Come be part of our mission as a") }}
					<span class="font-semibold text-red-500">{{ __("volunteer") }}</span>
					{{ __("or a") }}
					<span class="font-semibold text-red-500">{{ __("member") }}</span> !
				</p>
				<p class="text-gray-600 max-w-md">
					{{
						__(
							"Your time and passion can help change lives. Join us today and help build stronger, safer communities for everyone.",
						)
					}}
				</p>
			</div>

			<div class="flex flex-col items-center justify-center space-y-6">
				<div class="space-y-4 w-full max-w-sm">
					<Button
						variant="solid"
						theme="red"
						icon-right="arrow-right"
						class="w-full py-4 rounded-xl shadow-lg text-lg font-medium"
						@click="navigateTo('volunteer/signup')"
					>
						{{
							roleResource.data?.vol_applicant
								? __("Continue with Volunteer Registration")
								: __("Join as Volunteer")
						}}
					</Button>
					<Button
						variant="outline"
						theme="red"
						icon-right="arrow-right"
						class="w-full py-4 rounded-xl shadow-md text-lg font-medium"
						@click="navigateTo('membership')"
					>
						{{ __("Join as Member") }}
					</Button>
				</div>
			</div>
		</div>
	</div>

	<PendingApproval v-else-if="roleResource.data.is_pending_approval" />
</template>

<script setup>
import { Button } from "frappe-ui";
import router from "../router";
import { usersStore } from "../stores/user";
import PendingApproval from "./PendingApproval.vue";

const { roleResource } = usersStore();

function navigateTo(path) {
	router.push("/" + path);
}
</script>
