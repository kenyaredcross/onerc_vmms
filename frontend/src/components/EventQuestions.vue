<template>
	<div v-if="!formCompleted">
		<div class="bg-surface-white rounded-2xl shadow-lg overflow-hidden mb-2">
			<div class="bg-gradient-to-r from-red-500 to-red-600 px-8 py-10">
				<h1 class="text-3xl font-sans font-bold text-white mb-2">
					{{ eventDetail.data.title }}
				</h1>
				<p class="text-red-50 text-lg">{{ __("Event Registration") }}</p>
			</div>

			<div class="px-8 py-6 bg-surface-gray-50 border-b border-outline-gray-200">
				<div class="flex items-start gap-2">
					<Info class="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
					<p class="text-ink-gray-1-700 leading-relaxed">
						{{
							__(
								"Please fill in the following registration information. Fields marked with * are mandatory.",
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<div class="bg-surface-white rounded-2xl shadow-lg p-4 md:p-8">
			<h2
				class="text-2xl font-semibold text-ink-gray-1-800 mb-6 pb-4 border-b border-outline-gray-200"
			>
				{{ __("Registration Information") }}
			</h2>

			<div class="space-y-6">
				<div
					v-for="(question, index) in eventDetail.data.event_registration_questions"
					:key="index + 1"
					class="group"
				>
					<div class="rounded-xl md:p-6 transition-all duration-200 hover:shadow-md">
						<label class="block mb-3">
							<span class="text-ink-gray-1-900 font-medium text-lg flex items-start">
								<span
									class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-red-100 text-red-600 text-sm font-semibold mr-3 flex-shrink-0 mt-0.5"
								>
									{{ index + 1 }}
								</span>
								<span class="flex-1">
									{{ question.question }}
									<span v-if="question.is_required" class="text-red-500">*</span>
								</span>
							</span>
							<span
								v-if="question.help_text"
								class="block text-sm text-ink-gray-1-500 mt-2 ml-10"
							>
								{{ question.help_text }}
							</span>
						</label>

						<div class="ml-10">
							<Autocomplete
								v-if="question.question_type === 'MultiSelect'"
								:multiple="true"
								:options="question.options"
								:modelValue="getResponseValue(question.question_id)"
								@update:modelValue="
									populateResponses(
										question.question_id,
										question.question,
										$event,
									)
								"
								class="w-full"
							/>

							<FormControl
								v-else
								:type="textInputType(question.question_type)"
								:placeholder="question.help_text ? question.help_text : ''"
								:options="question.options"
								class="w-full"
								:modelValue="getResponseValue(question.question_id)"
								@update:modelValue="
									populateResponses(
										question.question_id,
										question.question,
										$event,
									)
								"
							/>
						</div>
					</div>
				</div>
				<ErrorMessage
					:message="errorMessage"
					class="mx-auto border border-red-500 rounded-md flex justify-center r p-2 md:w-3/4"
				/>

				<div class="flex justify-end">
					<Button variant="solid" theme="red" size="md" @click="handleRegister()">
						{{ __("Submit") }}
					</Button>
				</div>
			</div>
		</div>
	</div>
	<div v-else>
		<AttendEventModal
			v-if="!eventDetail.data.is_ticketed"
			:eventId="eventDetail.data.name"
			:eventName="eventDetail.data.title"
		/>
		<Ticket
			v-else
			:eventId="eventDetail.data.name"
			:tickets="eventDetail.data.tickets"
			:event="eventDetail.data.name"
			:eventDetails="eventDetail.data"
		/>
	</div>
</template>
<script setup>
import { FormControl, Button, Autocomplete, ErrorMessage } from "frappe-ui";
import { Info } from "lucide-vue-next";
import { ref, toRaw, watch } from "vue";
import { registrationResponses } from "../composables/RegistrationQuestions";
import AttendEventModal from "./Modals/AttendEventModal.vue";
import Ticket from "./Modals/Ticket.vue";

const responses = ref([]);
const errorMessage = ref("");
const formCompleted = ref(false);
const { addResponses } = registrationResponses();

const getResponseValue = (questionID) => {
	const responseEntry = responses.value.find((entry) => entry.question_id === questionID);
	return responseEntry ? responseEntry.response : null;
};

function populateResponses(questionID, question, response) {
	const existingIndex = responses.value.findIndex((entry) => entry.question_id === questionID);

	const responseEntry = {
		question_id: questionID,
		question: question,
		response: response,
	};
	if (existingIndex !== -1) {
		responses.value[existingIndex].response = response;
		return;
	} else {
		responses.value.push(responseEntry);
	}
}

const props = defineProps({
	eventDetail: {
		type: Object,
		required: true,
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
const handleRegister = () => {
	const requiredQuestions = props.eventDetail.data.event_registration_questions.filter(
		(question) => question.is_required,
	);
	for (const reqQuestion of requiredQuestions) {
		const answer = responses.value.find(
			(resp) => resp.question_id === reqQuestion.question_id,
		);
		if (!answer || !answer.response || answer.response.length === 0) {
			errorMessage.value = `Please provide input to the following question(s): "${reqQuestion.question}"`;
			return;
		}
	}
	errorMessage.value = "";
	saveResponses();
};

const saveResponses = () => {
	addResponses(toRaw(responses.value));
	formCompleted.value = true;
};
</script>
