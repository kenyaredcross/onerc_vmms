<template>
	<div class="w-full max-w-xs mx-auto">
		<div
			role="button"
			tabindex="0"
			@click="navigateEvent(event)"
			@keydown.enter="navigateEvent(event)"
			@keydown.space.prevent="navigateEvent(event)"
			class="w-full text-left flex flex-col rounded-2xl overflow-hidden border hover:shadow-2xl transition-all duration-500 bg-surface-base cursor-pointer"
		>
			<div class="relative w-full h-48">
				<img
					:src="event.banner_image"
					alt="Event Banner"
					class="w-full h-full object-cover rounded-2xl"
				/>
				<span class="absolute top-2 bg-red-500 p-1 rounded-md text-sm text-white ml-1">{{
					event.event_access
				}}</span>
			</div>

			<div
				class="flex border-b rounded-2xl border-b-red-500 flex-col bg-surface-base rounded-b-3xl px-5 py-6 space-y-3"
			>
				<div
					class="grid grid-cols-12 items-center justify-between text-ink-gray-1-700 text-sm gap-2"
				>
					<div class="col-span-3">
						<div
							class="flex flex-col items-center justify-center text-red-600 font-semibold leading-tight"
						>
							<span class="uppercase text-xs">
								{{ formatDate(event.start_date, "MMM") }}
							</span>
							<span class="text-3xl-bold">
								{{ formatDate(event.start_date, "D") }}
							</span>
						</div>
					</div>
					<div class="border-r-2 border-red-500 h-12"></div>
					<div class="flex items-center gap-1 col-span-8 font-bold">
						<MapPin class="w-4 h-4 text-red-500" />
						{{ event.venue }}
					</div>
				</div>

				<h2 class="text-lg-bold text-ink-gray-1-900">{{ event.title }}</h2>

				<p class="text-ink-gray-1-500 text-sm leading-snug line-clamp-2">
					{{ event.short_description }}
				</p>

				<div class="flex items-center gap-2 text-sm text-ink-gray-1-600">
					<Clock class="w-4 h-4 flex-shrink-0 text-red-500" />
					{{ formatTime(event.start_time) }}
				</div>
			</div>
		</div>
	</div>
	<PrivateEvent v-model="dialog" />
</template>
<script lang="ts" setup>
import { formatDate } from "@/utils/dayjs";
import { Badge, Button, Dialog } from "frappe-ui";
import { Calendar, Clock, MapPin } from "lucide-vue-next";
import { onMounted, ref } from "vue";
import PrivateEvent from "./Modals/PrivateEvent.vue";

const dialog = ref(false);

onMounted(() => {});

defineProps<{
	event: any;
}>();

function navigateEvent(event: any) {
	window.location.href = `/dashboard/book-tickets/${event.route}`;
}

function formatTime(timeStr: string) {
	const [hours, minutes] = timeStr.split(":").map(Number);
	const period = hours >= 12 ? "PM" : "AM";
	const formattedHours = hours % 12 || 12;
	return `${formattedHours}:${minutes.toString().padStart(2, "0")} ${period}`;
}
</script>
