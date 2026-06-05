<template>
	<Dialog
		v-model="attendeesModal"
		:options="{
			size: '4xl',
		}"
	>
		><template #body-title>
			<h3 class="text-2xl font-semibold text-ink-gray-9">Attendees</h3>
			<span class="text-gray-800">{{
				__(
					"Your tickets will automatically be sent to you and your guests. You will simply need to fill in their Name, Email address and phone number.",
				)
			}}</span>
			<br />
			<div
				class="flex items-center gap-2 text-sm text-red-600 border border-red-500 p-2 rounded-md mt-2 bg-red-50"
			>
				<AlertCircle :size="16" class="flex-shrink-0" />
				<span>{{
					__(
						"The First record is for the primary ticket holder and will be prompted for payment",
					)
				}}</span>
			</div>
		</template>
		<template #body-content>
			<div
				v-for="(attendee, index) in attendees"
				:key="index"
				class="space-y-2 md:space-y-5 md:flex items-center justify-center md:space-x-4"
			>
				<h1 class="text-gray-500 font-sans">Ticket #{{ index + 1 }}</h1>
				<Input
					required
					:name="`full_name_${index}`"
					type="text"
					placeholder="John Doe"
					label="Full Name"
					v-model="attendees[index].full_name"
				/>

				<Input
					required
					:name="`email_${index}`"
					type="email"
					placeholder="johndoe@email.com"
					label="Email"
					v-model="attendees[index].email"
				/>

				<Input
					required
					:name="`phone_${index}`"
					type="text"
					placeholder="0712345678"
					label="Phone Number"
					v-model="attendees[index].phone"
				/>
			</div>
			<ErrorMessage
				:message="errorMessage"
				class="w-1/2 mt-4 mx-auto border border-red-500 rounded-md p-2 flex justify-center"
			/>
		</template>
		<template #actions>
			<div class="flex justify-end space-x-2">
				<Button
					variant="solid"
					theme="green"
					@click="saveAttendeeFormData"
					:loading="loading"
				>
					Save
				</Button>
				<Button variant="outline" theme="red" @click="attendeesModal = false">
					Cancel
				</Button>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, Input, Button, ErrorMessage } from "frappe-ui";
import { toRaw, ref, watch } from "vue";
import { attendeeBooking } from "../../utils/booking";
import { AlertCircle } from "lucide-vue-next";

const attendeesModal = defineModel();
const loading = ref(false);
const errorMessage = ref("");
const emit = defineEmits(["update:attendees"]);

const props = defineProps({
	attendees: {
		type: Array,
		required: true,
	},
	edit: {
		type: Boolean,
		default: false,
	},
});

const saveAttendeeFormData = () => {
	loading.value = true;
	errorMessage.value = "";

	const attendeeData = toRaw(props.attendees);

	for (const attendee of attendeeData) {
		if (!attendee.full_name || !attendee.email || !attendee.phone) {
			errorMessage.value = "Please fill in all attendee details before saving.";
			loading.value = false;
			return;
		}
	}

	attendeeBooking.attendees = attendeeData;
	loading.value = false;
	attendeesModal.value = false;
	emit("update:attendees");
};

const cleanUpModal = () => {
	errorMessage.value = "";
	loading.value = false;
};

watch(attendeesModal, (newVal) => {
	if (!newVal) {
		cleanUpModal();
	}
});
</script>
