<template>
	<div class="max-w-3xl mx-auto my-auto p-6 bg-white rounded-2xl">
		<div class="flex items-center gap-4">
			<CalendarCheck class="w-6 h-6 text-green-600" />
			<h3 class="text-xl font-semibold text-gray-900">
				{{ registerSuccess ? "Registration Successful" : "Confirm Attendance" }}
			</h3>
		</div>

		<div v-if="!registerSuccess">
			<div class="space-y-4 mt-4">
				<p class="text-gray-700">
					You're about to register for the
					<span class="font-semibold text-red-500">{{ props.eventName }}</span> event.
					Once confirmed, you'll receive:
				</p>

				<div class="bg-green-50 border border-green-100 rounded-lg p-4 space-y-2">
					<div class="flex items-start gap-3">
						<Check class="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
						<span class="text-sm text-gray-700">
							<span class="font-semibold">Confirmation email</span> with event
							details
						</span>
					</div>
				</div>

				<div class="bg-red-50 border border-red-100 rounded-lg p-3">
					<p class="text-sm text-gray-700">
						<span class="font-semibold text-red-900">📅 Important:</span>
						Make sure to mark your calendar and arrive on time!
					</p>
				</div>
			</div>

			<div class="border p-2 mt-3 rounded-lg space-y-2">
				<span v-if="user.data === 'Guest'"
					>Please fill out the following information:</span
				>
				<form action="" @submit.prevent="submit">
					<div v-if="user.data === 'Guest'" class="space-y-2">
						<Input
							required
							name="first_name"
							type="text"
							autocomplete="name"
							placeholder="John Doe"
							label="Full Name"
							v-model="attendData.full_name"
						/>

						<Input
							required
							name="email"
							type="email"
							autocomplete="email"
							placeholder="johndoe@email.com"
							label="Email"
							v-model="attendData.email"
						/>

						<Input
							required
							name="phone"
							type="tel"
							autocomplete="tel"
							placeholder="0712345678"
							label="Phone Number"
							v-model="attendData.phone"
						/>
					</div>

					<div class="flex my-4 space-x-2 justify-center">
						<Button
							variant="solid"
							theme="green"
							size="sm"
							type="submit"
							:loading="confirmEvent.loading"
						>
							<span class="flex items-center gap-2">
								<Check class="w-4 h-4" />
								Confirm Attendance
							</span>
						</Button>
					</div>
					<ErrorMessage
						v-if="confirmEvent.error"
						:message="confirmEvent.error"
						class="text-center border border-red-400 rounded-md p-2"
					/>
				</form>
			</div>
		</div>

		<div v-else class="text-center space-y-4">
			<Check class="w-12 h-12 text-green-600 mx-auto" />
			<h2 class="text-2xl font-semibold text-gray-900">Registration Successful!</h2>
			<p class="text-gray-700">
				Thank you for registering! We look forward to seeing you at the event. You will
				receive a confirmation email shortly with all the event details.
			</p>
		</div>
	</div>
</template>

<script setup>
import { Button, createResource, Dialog, ErrorMessage, Input, toast } from "frappe-ui";
import { CalendarCheck, Check } from "lucide-vue-next";
import { inject, reactive, ref, watch } from "vue";
import { registrationResponses } from "../../composables/RegistrationQuestions";

const user = inject("$user");
const emit = defineEmits(["close"]);
const registerSuccess = ref(false);
const { formResponse, clearResponses } = registrationResponses();

const props = defineProps({
	dialogStatus: Boolean,
	eventId: String,
	eventName: String,
});
const attendData = reactive({
	full_name: user.data !== "Guest" ? user.data.full_name : "",
	phone: user.data !== "Guest" ? user.data.phone : "",
	email: user.data !== "Guest" ? user.data.email : "",
});

const confirmEvent = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.register_event",
	makeParams() {
		return {
			payload: {
				event_name: props.eventId,
				attendee: { ...attendData },
				registration_responses: formResponse.value,
			},
		};
	},
});

function submit() {
	confirmEvent.submit(
		{},
		{
			onSuccess() {
				registerSuccess.value = true;
				toast.success("You have successfully registered for the event.");
				clearResponses();
			},
		}
	);
}
</script>
