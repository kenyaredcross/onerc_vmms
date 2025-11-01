<template>
	<div class="w-full max-w-xs mx-auto">
		<div
			@click="navigateEvent(event)"
			class="flex flex-col rounded-2xl overflow-hidden border hover:shadow-2xl transition-all duration-500 bg-white cursor-pointer"
		>
			<div class="relative w-full h-48">
				<img
					:src="event.banner_image"
					alt="Event Banner"
					class="w-full h-full object-cover rounded-2xl"
				/>
			</div>

			<div
				class="flex border-b rounded-2xl border-b-red-500 flex-col bg-white rounded-b-3xl px-5 py-6 space-y-3"
			>
				<div class="flex items-center justify-between text-gray-700 text-sm">
					<div
						class="flex flex-col items-center justify-center text-red-600 font-semibold leading-tight"
					>
						<span class="uppercase text-xs">
							{{
								new Date(event.start_date).toLocaleDateString(undefined, {
									month: "short",
								})
							}}
						</span>
						<span class="text-2xl font-bold">
							{{ new Date(event.start_date).getDate() }}
						</span>
					</div>
					<div class="border-r-2 rounded-md border-red-500 h-12"></div>
					<div class="flex gap-2">
						<div class="flex items-center gap-1 text-sm">
							<MapPin class="w-4 h-4 text-red-500" />
							{{ event.venue }}
						</div>
						<Badge variant="outline" theme="orange">{{ event.event_access }}</Badge>
					</div>
				</div>

				<h2 class="text-lg font-bold text-gray-900">{{ event.title }}</h2>

				<p class="text-gray-500 text-sm leading-snug line-clamp-2">
					{{ event.short_description }}
				</p>

				<div class="flex items-center gap-2 text-sm text-gray-600">
					<Clock class="w-4 h-4 flex-shrink-0 text-red-500" />
					{{ formatTime(event.start_time) }}
				</div>
			</div>
		</div>
	</div>
	<PrivateEvent v-model="dialog" />
</template>
<script lang="ts" setup>
import { Badge, Button, Dialog } from "frappe-ui";
import { Calendar, Clock, MapPin } from "lucide-vue-next";
import { onMounted, ref } from "vue";
import router from "../router";
import { usersStore } from "../stores/user";
import PrivateEvent from "./Modals/PrivateEvent.vue";

const dialog = ref(false);

const { userResource } = usersStore();

onMounted(() => {});

defineProps<{
	event: any;
}>();

function navigateEvent(event: any) {
	if (event.event_access === "Private" && userResource.data == "Guest") {
		dialog.value = true;
	} else {
		router.push({ name: "EventDetail", params: { id: event.route } });
	}
}

function formatTime(timeStr: string) {
	const [hours, minutes] = timeStr.split(":").map(Number);
	const period = hours >= 12 ? "PM" : "AM";
	const formattedHours = hours % 12 || 12;
	return `${formattedHours}:${minutes.toString().padStart(2, "0")} ${period}`;
}
</script>
