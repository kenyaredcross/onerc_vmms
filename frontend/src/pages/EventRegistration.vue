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
					<div class="bg-white rounded-2xl shadow-lg overflow-hidden">
						<div class="bg-gradient-to-r from-red-500 to-red-600 px-8 py-10">
							<h1 class="text-3xl font-sans font-bold text-white mb-2">
								{{ eventDetail.data.title }}
							</h1>
							<p class="text-red-50 text-lg">Event Registration</p>
						</div>

						<div class="px-8 py-6 bg-gray-50 border-b border-gray-200">
							<div class="flex items-start gap-2">
								<Info class="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
								<p class="text-gray-700 leading-relaxed">
									Please complete all required fields marked with an asterisk (*)
									to register for this event.
								</p>
							</div>
						</div>
					</div>

					<div class="bg-white rounded-2xl shadow-lg p-4 md:p-8">
						<h2
							class="text-2xl font-semibold text-gray-800 mb-6 pb-4 border-b border-gray-200"
						>
							Registration Information
						</h2>

						<div class="space-y-6">
							<div
								v-for="(question, index) in eventDetail.data
									.event_registration_questions"
								:key="index + 1"
								class="group"
							>
								<div
									class="rounded-xl md:p-6 transition-all duration-200 hover:shadow-md"
								>
									<label class="block mb-3">
										<span
											class="text-gray-900 font-medium text-lg flex items-start"
										>
											<span
												class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-red-100 text-red-600 text-sm font-semibold mr-3 flex-shrink-0 mt-0.5"
											>
												{{ index + 1 }}
											</span>
											<span class="flex-1">
												{{ question.question }}
												<span
													v-if="question.is_required"
													class="text-red-500"
													>*</span
												>
											</span>
										</span>
										<span
											v-if="question.help_text"
											class="block text-sm text-gray-500 mt-2 ml-10"
										>
											{{ question.help_text }}
										</span>
									</label>

									<div class="ml-10">
										<Autocomplete
											v-if="question.question_type === 'MultiSelect'"
											:multiple="true"
											:options="question.options"
											v-model="people"
											class="w-full"
										/>

										<FormControl
											v-else
											:type="textInputType(question.question_type)"
											:placeholder="
												question.help_text ? question.help_text : ''
											"
											:options="question.options"
											class="w-full"
										/>
									</div>
								</div>
							</div>

							<div class="flex justify-end">
								<Button
									variant="solid"
									theme="red"
									size="md"
									@click="handleRegister(eventDetail.data.is_ticketed)"
								>
									Submit
								</Button>
							</div>
						</div>
					</div>
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
import {
	Autocomplete,
	Breadcrumbs,
	Button,
	createResource,
	ErrorMessage,
	FormControl,
	toast,
} from "frappe-ui";
import { inject, ref, watch } from "vue";
import { useRoute } from "vue-router";
import router from "../router";
import { sessionStore } from "../stores/session";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import { Info } from "lucide-vue-next";
import AttendEventModal from "../components/Modals/AttendEventModal.vue";
import Ticket from "../components/Modals/Ticket.vue";

const route = useRoute();
const people = ref([]);

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
				options, // ensure array always
			};
		});

		return {
			...data,
			event_registration_questions: transformedQuestions,
		};
	},
});

const textInputType = (eventDetailQuestionType) => {
	switch (eventDetailQuestionType) {
		case "Text":
			return "text";
		case "Select":
			return "select";
		case "Yes/No":
			return "select";
		case "Email":
			return "email";
		case "Phone":
			return "tel";
		case "Date":
			return "date";
		default:
			return "text";
	}
};

const handleRegister = (eventTicketStatus) => {
	console.log("Register button clicked with ticket status:", eventTicketStatus);
};
</script>
