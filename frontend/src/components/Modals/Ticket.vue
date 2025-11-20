<template>
	<div class="space-y-2">
		<h3 class="text-2xl font-bold text-gray-900">Select Your Ticket</h3>
		<p class="text-sm text-gray-500">Choose the perfect ticket for your experience</p>
	</div>

	<div v-if="!paymentStatus">
		<div
			:class="{
				'grid grid-cols-1 md:grid-cols-2 border': !selectedTicket,
				'grid grid-cols-1 md:grid-cols-2 gap-4': selectedTicket,
			}"
		>
			<div class="mt-6 space-y-3">
				<div
					v-for="ticket in props.tickets"
					:key="ticket.id"
					class="group relative overflow-hidden p-5 border-2 rounded-2xl bg-white cursor-pointer transition-all duration-300"
					:class="{
						'border-red-500 shadow-md shadow-red-100': selectedTicket === ticket.name,
						'border-gray-100 hover:border-red-300': selectedTicket !== ticket.name,
					}"
					@click="handleSelection(ticket)"
				>
					<div
						class="absolute top-0 right-0 w-32 h-32 bg-red-50 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 -mr-16 -mt-16"
					></div>

					<div class="relative flex items-start justify-between gap-4">
						<div class="flex-1">
							<div class="flex items-center gap-2 mb-2">
								<h4 class="text-lg font-semibold text-gray-900">
									{{ ticket.title }}
								</h4>
								<ChevronRight
									class="w-5 h-5 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
								/>
							</div>
						</div>

						<div class="flex flex-col items-end justify-between h-full">
							<div class="text-right">
								<div class="text-2xl font-bold text-gray-900">
									{{ ticket.price }}
								</div>
								<div class="text-xs text-gray-400 font-medium">
									{{ ticket.currency }}
								</div>
							</div>
						</div>
					</div>

					<Button
						class="w-full mt-4"
						theme="red"
						variant="solid"
						@click.stop="handleSelection(ticket)"
					>
						Select
					</Button>
				</div>
			</div>

			<div v-if="payStatus" class="mt-6 space-y-3">
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
				<Input
					v-if="user.data === 'Guest'"
					required
					name="email"
					type="email"
					placeholder="you@example.com"
					label="Email"
					v-model="ticketData.email"
				/>
				<Input
					v-if="user.data === 'Guest'"
					required
					name="first_name"
					type="text"
					placeholder="Jane Doe"
					label="Full Name"
					v-model="ticketData.full_name"
				/>

				<Input
					required
					name="phone"
					type="text"
					placeholder="0712345678"
					label="MPesa Phone Number  for payment"
					v-model="ticketData.phone"
				/>
				<div class="flex flex-col gap-2">
					<label class="text-sm text-gray-700 mb-2"> Number of Tickets </label>
					<div class="flex items-center gap-3">
						<Button
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
							@input="handleTicketsNumber($event.target.value)"
							class="w-20 text-center border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-red-500 focus:border-transparent"
						/>
						<Button theme="green" variant="outline" @click="numberOfTickets++">
							+
						</Button>
					</div>
				</div>

				<PaymentInfoAlert v-if="checkSTK" />
				<Button
					v-if="!confirmPayment && payStatus"
					class="w-full mt-4"
					theme="green"
					variant="solid"
					@click="proceedToPay"
					:loading="handlePay.loading || confirmPaymentStatus.loading"
				>
					{{
						handlePay.loading
							? "Initialising Payment"
							: confirmPaymentStatus.loading
								? "Confirming Payment"
								: "Proceed to Pay"
					}}
				</Button>
			</div>
		</div>

		<ErrorMessage
			v-if="handlePay.error"
			:message="handlePay.error"
			class="w-1/2 text-center border border-red-400 rounded-md p-2 mt-3"
		/>

		<Button
			v-if="confirmPayment"
			class="w-full mt-4"
			theme="green"
			variant="solid"
			@click="checkPayment"
			:loading="confirmPaymentStatus.loading"
		>
			Confirm Payment
		</Button>
	</div>
	<PaymentStatus
		v-if="paymentStatus"
		@close="openTicketModal = false"
		message="Ticket booked successfully. You will receive an email with your ticket details."
		title="Ticket"
	/>
</template>

<script setup>
import { Button, createResource, ErrorMessage, Input, TextInput, toast } from "frappe-ui";
import { ChevronRight } from "lucide-vue-next";
import { computed, inject, reactive, ref } from "vue";
import PaymentStatus from "../PaymentStatus.vue";
import { sessionStore } from "../../stores/session";
import PaymentInfoAlert from "../PaymentInfoAlert.vue";
import { PaymentListener } from "../../utils/payment";

const openTicketModal = defineModel();
const payStatus = ref(false);
const amount = computed(() => {
	return `${ticketData.currency} ${ticketData.price}`;
});
const selectedTicket = ref(null);
const user = inject("$user");
const invoice = ref("");
const eventBooking = ref("");
const paymentStatus = ref(false);
const confirmPayment = ref(null);
const confirm_payment_manual = ref(false);
const { isLoggedIn } = sessionStore();
const checkSTK = ref(false);
const numberOfTickets = ref(1);

const ticketData = reactive({
	ticket_type: "",
	price: "",
	currency: "",
	phone: isLoggedIn ? user.data.phone : "",
	ticket_name: "",
	email: isLoggedIn ? user.data.email : "",
	full_name: isLoggedIn ? user.data.full_name : "",
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
});

const ticketTotal = computed(() => {
	return ticketData.price * numberOfTickets.value;
});

function handleSelection(ticket) {
	selectedTicket.value = ticket.name;
	payStatus.value = true;
	ticketData.ticket_type = ticket.title;
	ticketData.price = ticket.price;
	ticketData.currency = ticket.currency;
	ticketData.ticket_name = ticket.name;
	numberOfTickets.value = 1;
}

const handlePay = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.handle_ticket_payment",
	makeParams() {
		return {
			payload: {
				event_name: props.event,
				phone: ticketData.phone,
				ticket_name: ticketData.ticket_name,
				email: ticketData.email,
				full_name: ticketData.full_name,
			},
		};
	},
	onSuccess(data) {
		if (data) {
			checkSTK.value = true;
			toast.success(
				"Payment initiated successfully. Please complete the payment on your phone.",
			);
			invoice.value = data.invoice;
			eventBooking.value = data.event_booking;
			confirmPaymentStatus.loading = true;
			initiatePaymentListener(data);
		}
	},
	onError(error) {
		handlePay.error = "An error occurred during payment. Please try again.";
	},
});

function validatePhone(phone) {
	const phoneRegex = /^07\d{8}$/;
	return phoneRegex.test(phone);
}

function initiatePaymentListener(data) {
	const paymentInstance = new PaymentListener();
	paymentInstance.saveToken(data.payment_token);
	paymentInstance.listenForPayment().then((status) => {
		confirmPaymentStatus.loading = false;
		status === "Completed"
			? (paymentStatus.value = true)
			: ((checkSTK.value = false),
				(handlePay.error =
					"There was an error processing your payment. Please try again."));
	});
}

function proceedToPay() {
	if (user.data == "Guest") {
		if (!ticketData.email || !ticketData.full_name || !ticketData.phone) {
			handlePay.error = "All fields are required";
			return;
		}
	} else {
		if (!ticketData.phone) {
			handlePay.error = "Phone number is required";
			return;
		}

		if (!validatePhone(ticketData.phone)) {
			handlePay.error = "Invalid phone number format. Please use 0712345678 format";
			return;
		}
	}
	handlePay.submit({});
}

const confirmPaymentStatus = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.confirm_payment",
	makeParams() {
		return {
			invoice_name: invoice.value,
			event_booking: eventBooking.value,
			confirm_payment_manual: confirm_payment_manual.value,
		};
	},
});

const checkPayment = (checkPaymentManual) => {
	if (!invoice.value) {
		toast.error("Error confirming payment. Please try again.");
		return;
	}

	if (checkPaymentManual) {
		toast.info("Checking payment status. Please wait...");
	}
	confirmPaymentStatus.submit(
		{},
		{
			onSuccess(data) {
				if (data === "paid") {
					toast.success("Payment confirmed! Your ticket has been booked.");
					paymentStatus.value = true;
				} else {
					toast.error("Payment timeout. Please try again or confirm Payment");
					confirmPayment.value = true;
				}
			},
			onError() {
				toast.error("Error confirming payment. Please try again.");
			},
		},
	);
};
const handleTicketsNumber = (val) => {
	const parsed = Number(val);

	// If invalid, zero, negative, NaN → force to 1
	numberOfTickets.value = parsed >= 1 ? parsed : 1;
};
</script>
