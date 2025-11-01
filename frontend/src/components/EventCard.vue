<template>
	<div class="py-2 px-4">
		<div class="max-w-3xl mx-auto space-y-2">
			<div class="mb-2">
				<div
					@click="navigateEvent(event)"
					class="flex flex-col md:flex-row items-stretch rounded-lg shadow-sm overflow-hidden bg-white cursor-pointer"
				>
					<div
						class="flex flex-col items-center justify-center bg-red-100 px-6 py-4 border-b md:border-b-0 md:border-r border-gray-100 w-full md:w-40"
					>
						<div class="text-3xl font-bold text-red-600">
							{{ __(new Date(event.start_date).getDate()) }}
						</div>
						<div class="text-xs text-gray-600">
							{{
								__(
									new Date(event.start_date).toLocaleString("default", {
										month: "short",
										year: "numeric",
									}),
								)
							}}
						</div>
						<img
							:src="event.banner_image"
							:alt="__('Event Banner')"
							class="mt-1 rounded-md p-1"
						/>
					</div>

					<div class="flex-1 p-5">
						<div
							class="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-3 gap-2"
						>
							<div class="flex-1">
								<h3 class="text-lg font-semibold text-gray-900 mb-1">
									{{ __(event.title) }}
								</h3>
								<p class="text-sm text-gray-600 mb-2 line-clamp-2">
									{{ __(event.short_description) }}
								</p>
								<div class="flex items-center text-sm text-gray-500 mb-2">
									<MapPin class="w-4 h-4 mr-1.5 flex-shrink-0" />
									<span class="truncate">{{ __(event.venue) }}</span>
								</div>
							</div>
						</div>

						<div
							class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
						>
							<div class="flex flex-wrap items-center gap-4 text-sm text-gray-600">
								<div class="flex items-center">
									<Clock class="w-4 h-4 mr-1.5 text-red-500" />
									<span>{{ __(event.start_time) }}</span>
								</div>
								<div class="flex items-center">
									<Calendar class="w-4 h-4 mr-1.5 text-red-500" />
									<span>{{ __(event.start_date) }}</span>
								</div>
								<div class="flex items-center">
									<Badge :variant="'outline'" theme="blue">{{
										__(event.event_access)
									}}</Badge>
								</div>
							</div>

							<Button :variant="'solid'" :icon="'arrow-right'" :theme="'red'">
								{{ __("View Details") }}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
	<PrivateEvent v-model="dialog" />
</template>

<script setup>
import { Badge, Button } from "frappe-ui";
import { Calendar, Clock, MapPin } from "lucide-vue-next";
import { onMounted, ref } from "vue";
import router from "../router";
import { usersStore } from "../stores/user";
import PrivateEvent from "./Modals/PrivateEvent.vue";

const dialog = ref(false);

const { userResource } = usersStore();

onMounted(() => {});

defineProps({
	event: Object,
});

function navigateEvent(event) {
	if (event.event_access === "Private" && userResource.data == "Guest") {
		dialog.value = true;
	} else {
		router.push({ name: "EventDetail", params: { id: event.route } });
	}
}
</script>
