<template>
	<div>
		<div class="space-y-2">
			<h3 class="text-2xl font-bold text-gray-900">Select Your Ticket</h3>
			<p class="text-sm text-gray-500">Choose the perfect ticket for your experience</p>
		</div>
		<div
			:class="{
				'grid grid-cols-1 md:grid-cols-2': !selectedTicket,
				'grid grid-cols-1 md:grid-cols-2 gap-4': selectedTicket,
			}"
		>
			<div class="mt-6 space-y-3">
				<div
					v-for="ticket in props.tickets"
					:key="ticket.id"
					:class="{
						'border-2 border-red-500 rounded-2xl shadow-md shadow-red-100':
							selectedTicket === ticket.name,
						'border-gray-100 hover:border-red-300': selectedTicket !== ticket.name,
					}"
					@click="handleSelection(ticket)"
				>
					<TicketCard :ticket="ticket" />
				</div>
			</div>

			<form v-if="payStatus" class="mt-6 space-y-3" @submit.prevent="proceedToPay">
				<Input
					name="ticket_type"
					type="text"
					label="Ticket Type"
					v-model="ticketData.ticket_type"
					readonly
				/>
				<Input
					name="price"
					type="text"
					label="Price"
					:value="ticketTotal"
					v-model="ticketData.price"
					readonly
				/>
				<div v-if="shouldShowTicketNumber" class="flex flex-col gap-2">
					<label class="text-sm text-gray-700 mb-2">{{ __("Number of Tickets") }}</label>
					<div class="flex items-center gap-3">
						<Button
							type="button"
							theme="blue"
							variant="outline"
							@click="numberOfTickets = Math.max(1, numberOfTickets - 1)"
							:disabled="numberOfTickets <= 1"
						>
							-
						</Button>
						<input
							type="number"
							v-model.number="numberOfTickets"
							min="1"
							max="10"
							@input="handleTicketsNumber($event.target.value)"
							class="w-20 h-10 text-center border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-red-500 focus:border-transparent"
						/>
						<Button
							type="button"
							theme="green"
							variant="outline"
							@click="numberOfTickets++"
							:disabled="numberOfTickets >= 10"
						>
							+
						</Button>
					</div>
				</div>

				<Button
					theme="red"
					variant="solid"
					@click="saveTicketDetails"
					type="button"
					class="w-full mt-4"
					>{{ __("Get Tickets") }}</Button
				>
			</form>
		</div>
	</div>

	<Attendees
		v-model="attendeesModal"
		:attendees="attendeeFormData"
		:edit="editAttendees"
		@update:attendees="goToCheckout"
	/>
</template>

<script setup>
import { Button, Input } from "frappe-ui";
import { computed, inject, reactive, ref, toRaw, watch } from "vue";
import { sessionStore } from "../../stores/session";
import Attendees from "./Attendees.vue";
import { attendeeBooking } from "../../utils/booking";
import TicketCard from "../TicketCard.vue";
import router from "../../router";

const payStatus = ref(false);
const selectedTicket = ref(null);
const user = inject("$user");
const { isLoggedIn } = sessionStore();
const numberOfTickets = ref(1);
const attendeesModal = ref(false);
const attendeeFormData = ref([{ full_name: "", email: "", phone: "" }]);
const editAttendees = ref(false);

const ticketData = reactive({
	ticket_type: "",
	price: "",
	currency: "",
	ticket_category: "",
	ticket_capacity: "",
	phone: isLoggedIn ? user.data.phone : "",
	ticket_name: "",
	email: isLoggedIn ? user.data.email : "",
	full_name: isLoggedIn ? user.data.full_name : "",
});

watch(numberOfTickets, (newVal) => {
	if (newVal < 1) {
		attendeeFormData.value = [];
		return;
	}

	attendeeFormData.value = Array.from({ length: newVal }, () => ({
		full_name: "",
		email: "",
		phone: "",
	}));
});

const props = defineProps({
	tickets: {
		type: Array,
		required: true,
	},

	event: {
		type: String,
		required: true,
	},
	eventDetails: {
		type: Object,
		required: false,
	},
});

const hasRegistrationQuestions = computed(
	() => props.eventDetails?.event_registration_questions?.length > 0
);
const ticketTotal = computed(() => {
	return ticketData.price * numberOfTickets.value;
});
const shouldShowTicketNumber = computed(() => {
	return !hasRegistrationQuestions.value && ticketData.ticket_category === "Individual";
});
const goToCheckout = () => {
	router.push({
		name: "CheckoutSummary",
	});
};

const saveTicketDetails = () => {
	const selectedTicket = toRaw(ticketData);

	if (selectedTicket.ticket_category === "Group") {
		attendeeFormData.value = Array.from({ length: selectedTicket.ticket_capacity }, () => ({
			full_name: "",
			email: "",
			phone: "",
		}));
	}
	attendeesModal.value = true;

	attendeeBooking.TicketDetails = {
		ticket_type: selectedTicket.ticket_name,
		number_of_tickets: numberOfTickets.value,
		total_price: ticketTotal.value,
	};
};
function handleSelection(ticket) {
	selectedTicket.value = ticket.name;
	payStatus.value = true;
	ticketData.ticket_type = ticket.title;
	ticketData.price = ticket.price;
	ticketData.currency = ticket.currency;
	ticketData.ticket_name = ticket.name;
	ticketData.ticket_category = ticket.ticket_type;
	ticketData.ticket_capacity = ticket.ticket_capacity;

	numberOfTickets.value = 1;
}

const handleTicketsNumber = (val) => {
	const parsed = Number(val);

	numberOfTickets.value = parsed >= 1 ? parsed : 1;
};

watch(attendeesModal, (newVal) => {
	if (!newVal) {
		attendeeFormData.value = [{ full_name: "", email: "", phone: "" }];
	}
});
</script>
