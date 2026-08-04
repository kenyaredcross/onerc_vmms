<template>
	<Breadcrumbs
		v-if="eventDetail.data"
		:items="[
			{
				label: 'Events',
				route: '/events',
			},
			{
				label: eventDetail.data.title,
				route: '/event/' + eventDetail.data.route,
			},
		]"
		class="my-4 max-w-4xl px-4"
	/>
	<div
		class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100"
		:aria-busy="eventDetail.loading"
	>
		<ProgressSpinner v-if="eventDetail.loading" />
		<ErrorMessage
			v-else-if="eventDetail.error"
			class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20"
			:message="__('Failed to load Event Details')"
		/>
		<div v-else-if="eventDetail.data">
			<div class="relative overflow-hidden bg-white">
				<div class="absolute inset-0 bg-gradient-to-r from-red-300 to-transparent"></div>
				<div
					class="max-w-7xl mx-auto px-4 sm:px-2 lg:px-8 py-8 lg:py-10 relative flex flex-col md:flex-row items-center gap-4 md:gap-10"
				>
					<div class="flex-1">
						<h1
							class="text-3xl lg:text-[2.0rem] font-bold text-gray-800 mb-4 leading-tight"
						>
							{{ __(eventDetail.data?.title) }}
						</h1>

						<div class="flex flex-wrap gap-4 sm:gap-6 text-gray-700 mb-4 sm:mb-6">
							<div class="flex items-center gap-2 text-sm sm:text-base">
								<CalendarDays class="w-5 h-5 text-red-500" />
								<span
									>{{ formatDate(eventDetail.data?.start_date) }} {{ __("-") }}
									{{ formatDate(eventDetail.data?.end_date) }}</span
								>
							</div>
							<div class="flex items-center gap-2 text-sm sm:text-base">
								<Clock class="w-5 h-5 text-red-500" />
								<span>{{ __(eventDetail.data?.start_time) }}</span>
							</div>
							<div class="flex items-center gap-2 text-sm sm:text-base">
								<MapPin class="w-5 h-5 text-red-500" />
								<span>{{ __(eventDetail.data?.venue) }}</span>
							</div>
						</div>

						<div class="mb-6 sm:mb-8" v-if="!eventDetail.data.is_past_event">
							<Button
								theme="red"
								variant="solid"
								size="lg"
								@click="handleRegister(eventDetail.data.route)"
							>
								{{
									eventDetail.data.is_ticketed
										? __("Get Tickets")
										: __("Register ")
								}}
							</Button>
						</div>

						<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
							<div
								v-for="(value, key) in timeRemaining"
								:key="key"
								class="bg-red-50 border border-red-100 rounded-lg py-3 px-1 sm:py-4 text-center"
							>
								<div class="text-xl sm:text-3xl font-bold text-gray-800">
									{{ value }}
								</div>
								<div class="text-xs sm:text-sm text-gray-600 uppercase mt-1">
									{{ key }}
								</div>
							</div>
						</div>
					</div>

					<div class="w-64 h-64 sm:w-80 sm:h-80 lg:w-96 lg:h-96 flex-shrink-0">
						<img
							:src="eventDetail.data?.banner_image"
							:alt="__('Event Image')"
							class="w-full h-full object-cover rounded-lg shadow-xl"
						/>
					</div>
				</div>
			</div>

			<div class="max-w-7xl mx-auto md:px-4 px-1 lg:px-8 p-2 flex flex-col gap-2">
				<div v-if="eventDetail.data?.short_description">
					<div class="bg-white border border-gray-200 rounded-2xl p-6 sm:p-12 shadow-sm">
						<h2 class="text-xl md:text-3xl font-extrabold text-red-500 mb-3">
							{{ __("Why attend?") }}
						</h2>
						<p class="text-base sm:text-lg text-gray-700 leading-relaxed mb-6">
							{{ __(eventDetail.data?.short_description) }}
						</p>
						<hr class="my-4" />
						<p class="text-base sm:text-lg text-gray-700 leading-relaxed mb-6">
							{{ __(eventDetail.data?.about) }}
						</p>
					</div>
				</div>

				<div>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
						<div
							v-if="eventDetail.data?.speakers?.length"
							class="md:col-span-2 bg-white rounded-xl p-6 border border-gray-200 shadow-sm"
						>
							<div class="mb-6 flex items-center gap-3">
								<div
									class="w-10 h-10 flex items-center justify-center rounded-lg bg-red-50 border border-red-100"
								>
									<Users class="w-5 h-5 text-red-500" />
								</div>
								<h3 class="text-xl md:text-3xl font-extrabold text-gray-900">
									{{ __("Featured Speakers") }}
								</h3>
							</div>

							<ul class="space-y-4">
								<li
									v-for="speaker in eventDetail.data?.speakers"
									:key="speaker.name"
									class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gray-50 border border-gray-200 rounded-lg p-4"
								>
									<div class="flex items-center gap-4">
										<img
											:src="speaker.display_image"
											:alt="__('Speaker Image')"
											class="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover border border-gray-200"
										/>
										<div class="flex flex-col gap-1">
											<h4 class="text-lg font-semibold text-gray-800">
												{{ __(speaker.display_name) }}
											</h4>
											<p class="text-sm text-gray-600">
												{{ __(speaker.designation) }}
											</p>
											<p
												class="text-red-500 font-bold"
												v-if="speaker.company"
											>
												{{ __(speaker.company) }}
											</p>
										</div>
									</div>
								</li>
							</ul>
						</div>
					</div>
				</div>

				<div
					v-if="eventDetail.data?.host"
					class="bg-white rounded-xl p-6 border border-gray-200 shadow-sm"
				>
					<div class="mb-6 flex items-center gap-3">
						<div
							class="w-10 h-10 flex items-center justify-center rounded-lg bg-red-50 border border-red-100"
						>
							<Users class="w-5 h-5 text-red-500" />
						</div>
						<h3 class="text-xl md:text-3xl font-extrabold text-gray-900">
							{{ __("Meet The Host") }}
						</h3>
					</div>

					<div class="bg-gray-50 border border-gray-200 rounded-lg p-6">
						<div class="flex flex-row px-4 items-center gap-4 mb-2">
							<img
								:src="eventDetail.data.host.logo"
								alt=""
								class="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover border border-gray-200"
							/>
							<h4 class="text-3xl font-semibold text-red-500 mb-3">
								{{ __(eventDetail.data.host.name) }}
							</h4>
						</div>
						<p class="text-base text-gray-700 leading-relaxed mb-4">
							{{ __(eventDetail.data.host.about) }}
						</p>
						<div
							v-if="eventDetail.data.host.address"
							class="flex items-center gap-2 text-sm text-gray-600"
						>
							<MapPin class="w-4 h-4 text-red-500" />
							<span>{{ __(eventDetail.data.host.address) }}</span>
						</div>
					</div>
				</div>

				<div
					v-if="eventDetail.data?.sponsors?.length"
					class="bg-white rounded-xl p-6 border border-gray-200 shadow-sm"
				>
					<div class="mb-6 flex items-center gap-3">
						<h3 class="text-xl md:text-3xl font-extrabold text-gray-900">
							{{ __("Our Sponsors") }}
						</h3>
					</div>
					<div
						v-if="eventDetail.data?.sponsors"
						class="bg-gray-50 border border-gray-200 rounded-lg p-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
					>
						<a
							:href="sponsor.website"
							v-for="sponsor in eventDetail.data.sponsors"
							:key="sponsor.name"
							class="flex items-center gap-2 text-sm text-gray-600"
						>
							<img
								:src="sponsor.company_logo"
								:alt="__('Sponsor Logo')"
								class="w-32 h-16 object-contain"
							/>
						</a>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { formatDate } from "@/utils/dayjs";
import { Breadcrumbs, Button, createResource, toast } from "frappe-ui";
import ErrorMessage from "frappe-ui/src/components/ErrorMessage/ErrorMessage.vue";
import { CalendarDays, Clock, MapPin, Users } from "lucide-vue-next";
import { computed, inject, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import router from "../router";

const route = useRoute();
const eventName = ref(route.params.id);
const user = inject("$user");

const eventDetail = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.get_event_details",
	makeParams() {
		return {
			event_name: eventName.value,
		};
	},
	auto: true,
	cache: ["event", eventName.value],
	onSuccess() {
		if (
			user?.data == "Guest" &&
			(eventDetail.data?.event_access === "Private" ||
				eventDetail.data?.event_access === "Members Only")
		) {
			toast.error("This is a private event. Please log in  to view event details.");
			setTimeout(() => {
				router.push({ name: "Login" });
			}, 3000);
		}
	},
});

const timeRemaining = ref({
	days: 0,
	hours: 0,
	minutes: 0,
	seconds: 0,
});

let timerInterval = null;

const start_date = computed(() => {
	return eventDetail.data?.start_date || "";
});
const start_time = computed(() => {
	return eventDetail.data?.start_time || "";
});

watch([start_date, start_time], () => {
	if (start_date.value && start_time.value) {
		calculateTimeRemaining();
		if (timerInterval) {
			clearInterval(timerInterval);
		}
		timerInterval = setInterval(calculateTimeRemaining, 1000);
	}
});

const calculateTimeRemaining = () => {
	if (!start_date.value || !start_time.value) {
		return;
	}

	let timeStr = start_time.value.trim();
	if (!timeStr.includes(":")) {
		return;
	}

	let timeParts = timeStr.split(":");
	timeParts = timeParts.map((part) => part.padStart(2, "0"));

	if (timeParts.length === 2) {
		timeParts.push("00");
	}

	timeStr = timeParts.join(":");

	const dateTimeStr = `${start_date.value}T${timeStr}`;
	const startDateTime = new Date(dateTimeStr);

	if (isNaN(startDateTime.getTime())) {
		return;
	}

	const now = new Date();
	const difference = startDateTime - now;

	if (difference > 0) {
		timeRemaining.value = {
			days: Math.floor(difference / (1000 * 60 * 60 * 24)),
			hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
			minutes: Math.floor((difference / 1000 / 60) % 60),
			seconds: Math.floor((difference / 1000) % 60),
		};
	} else {
		timeRemaining.value = {
			days: 0,
			hours: 0,
			minutes: 0,
			seconds: 0,
		};
	}
};

const handleRegister = (route) => {
	window.location.href = `/vmms/event/registration/${route}`;
};

onMounted(() => {
	calculateTimeRemaining();
	timerInterval = setInterval(calculateTimeRemaining, 1000);
});

onUnmounted(() => {
	if (timerInterval) {
		clearInterval(timerInterval);
	}
});
</script>
