<template>
	<div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-2 md:py-8 px-4">
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
				{
					label: 'Registration',
				},
			]"
			class="mb-6 max-w-4xl mx-auto"
		/>
		<div class="max-w-4xl mx-auto">
			<div v-if="eventDetail.loading" class="flex items-center justify-center py-20">
				<ProgressSpinner />
			</div>

			<div v-else-if="eventDetail.error" class="bg-white rounded-2xl shadow-lg p-8">
				<ErrorMessage message="Failed to load event details." />
			</div>
			<div v-else-if="eventDetail.data">
				<div class="space-y-6" v-if="eventDetail.data.event_registration_questions.length">
					<EventQuestions :eventDetail="eventDetail" />
				</div>
				<div v-else-if="!eventDetail.data.is_ticketed">
					<AttendEventModal
						:eventId="eventDetail.data.name"
						:eventName="eventDetail.data.title"
					/>
				</div>
				<div
					v-else-if="
						!eventDetail.data.event_registration_questions.length &&
						eventDetail.data.is_ticketed
					"
				>
					<Ticket
						:eventId="eventDetail.data.name"
						:tickets="eventDetail.data.tickets"
						:event="eventDetail.data.name"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import { Breadcrumbs, createResource, ErrorMessage, toast } from "frappe-ui";
import { ref } from "vue";
import { useRoute } from "vue-router";
import router from "../router";
import { sessionStore } from "../stores/session";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import AttendEventModal from "../components/Modals/AttendEventModal.vue";
import Ticket from "../components/Modals/Ticket.vue";
import EventQuestions from "../components/EventQuestions.vue";

const route = useRoute();

const eventRoute = ref(route.params.eventRoute);
const { isLoggedIn } = sessionStore();

const eventDetail = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.get_event_details",
	makeParams() {
		return {
			event_name: eventRoute.value,
		};
	},
	auto: true,
	cache: ["event", eventRoute.value],
	onSuccess(data) {
		if (
			!isLoggedIn &&
			(eventDetail.data?.event_access === "Private" ||
				eventDetail.data?.event_access === "Members Only")
		) {
			toast.error("This is a private event. Please log in  to view event details.");
			setTimeout(() => {
				router.push({ name: "Login" });
			}, 4000);
		}
	},
	transform(data) {
		const transformedQuestions = data.event_registration_questions.map((question) => {
			let options = [];

			if (["Select", "Yes/No", "MultiSelect"].includes(question.question_type)) {
				if (typeof question.options === "string") {
					options = question.options
						.split("\n")
						.map((opt) => opt.trim())
						.filter(Boolean)
						.map((opt) => ({ label: opt, value: opt }));
				}
			}

			return {
				...question,
				options,
			};
		});

		return {
			...data,
			event_registration_questions: transformedQuestions,
		};
	},
});
</script>
