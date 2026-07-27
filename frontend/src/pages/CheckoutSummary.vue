<template>
	<div class="min-h-screen bg-gray-50 py-3 md:py-6 px-3 md:px-4">
		<Breadcrumbs
			v-if="ticketType.data"
			:items="[
				{
					label: 'Events',
					route: '/events',
				},
				{
					label: ticketType.data.event_details?.title,
					route: '/event/' + ticketType.data.event_details?.route,
				},
				{
					label: 'Registration',
					route: '/event/registration/' + ticketType.data.event_details?.route,
				},
				{ label: 'Checkout Summary' },
			]"
			class="mx-4 my-4"
		/>
		<div v-else class="flex flex-col sm:w-1/2 mx-auto bg-gray-50 py-3 md:py-6 px-3 md:px-4">
			<EmptyState type="Event Bookings" />
			<Button
				type="button"
				class="mt-4 mx-auto block"
				theme="red"
				variant="solid"
				@click="$router.push('/events')"
			>
				{{ __("Browse Events") }}
			</Button>
		</div>

		<div>
			<div v-if="!paymentStatus">
				<div v-if="ticketType.data" class="">
					<div class="max-w-5xl mx-auto">
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4">
							<div class="space-y-3">
								<div
									class="bg-white rounded-lg shadow-sm border border-gray-200 p-3 md:p-4"
								>
									<h1 class="text-lg md:text-xl font-semibold text-gray-900">
										Booked Ticket Type
									</h1>
								</div>

								<TicketCard :ticket="ticketType.data" />

								<div
									class="bg-white shadow-sm rounded-lg p-3 md:p-4 border border-gray-200"
								>
									<h2
										class="text-base md:text-lg font-semibold text-red-600 mb-3"
									>
										Booking Summary
									</h2>

									<div class="mb-3 pb-3 border-b border-gray-100">
										<p class="text-xs text-gray-500 mb-0.5">Event</p>
										<h2 class="text-sm md:text-base font-medium text-gray-900">
											{{ ticketType.data?.event_details?.title }}
										</h2>
									</div>

									<h3
										class="text-sm md:text-base font-semibold text-gray-800 mb-2"
									>
										Attendee Details
									</h3>

									<div class="space-y-2">
										<div
											v-for="(att, i) in attendeeBooking.getBookingData()
												.attendees"
											:key="i"
											class="bg-red-50 border border-red-100 rounded-lg p-2.5 md:p-3"
										>
											<div class="flex items-center gap-2 mb-1.5">
												<div
													class="w-5 h-5 bg-red-600 rounded-full flex items-center justify-center flex-shrink-0"
												>
													<span class="text-white font-medium text-xs">{{
														i + 1
													}}</span>
												</div>
												<p
													class="text-xs md:text-sm font-medium text-gray-800"
												>
													Attendee {{ i + 1 }}
												</p>
											</div>
											<div
												class="space-y-1 text-xs md:text-sm text-gray-700"
											>
												<p>
													<span class="font-medium">Name:</span>
													{{ att.full_name }}
												</p>
												<p>
													<span class="font-medium">Email:</span>
													{{ att.email }}
												</p>
												<p>
													<span class="font-medium">Phone:</span>
													{{ att.phone }}
												</p>
											</div>
										</div>
									</div>
								</div>
							</div>

							<div class="lg:sticky lg:top-3 lg:self-start">
								<div
									class="bg-white shadow-sm rounded-lg p-3 md:p-4 border border-gray-200"
								>
									<h2
										class="text-base md:text-lg font-semibold text-red-600 mb-3"
									>
										Payment Summary
									</h2>

									<div class="space-y-2.5">
										<div
											class="flex justify-between items-center py-2 border-b border-gray-100"
										>
											<span class="text-xs md:text-sm text-gray-600"
												>Total Tickets</span
											>
											<span
												class="text-sm md:text-base font-semibold text-gray-900"
											>
												{{
													attendeeBooking.getBookingData().attendees
														.length
												}}
											</span>
										</div>

										<div
											class="flex justify-between items-center py-2 border-b border-gray-100"
										>
											<span class="text-xs md:text-sm text-gray-600"
												>Price Per Ticket</span
											>
											<span
												class="text-sm md:text-base font-semibold text-gray-900"
											>
												{{ ticketType.data?.price || 0 }}
											</span>
										</div>

										<div class="bg-red-600 rounded-lg p-3 md:p-4 mt-3">
											<div class="flex justify-between items-center">
												<span
													class="text-white font-semibold text-sm md:text-base"
													>Total Amount</span
												>
												<span
													class="text-white font-bold text-lg md:text-2xl"
												>
													{{
														(ticketType.data?.price || 0) *
														attendeeBooking.getBookingData().attendees
															.length
													}}
												</span>
											</div>
										</div>
									</div>
								</div>

								<PaymentInfoAlert v-if="checkSTK" class="mt-4" />

								<div>
									<Button
										type="button"
										class="w-full mt-4"
										theme="green"
										variant="solid"
										@click="proceedToPay"
										:loading="
											handlePay.loading || confirmPaymentStatus.loading
										"
									>
										{{
											handlePay.loading
												? __("Initialising Payment")
												: confirmPaymentStatus.loading
												? __("Confirming Payment")
												: __("Proceed to Pay")
										}}
									</Button>
								</div>
								<ErrorMessage
									v-if="handlePay.error"
									:message="handlePay.error"
									class="text-center border border-red-400 rounded-md p-2 mt-3"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div v-else class="sm:w-1/2 mx-auto bg-gray-50 py-3 md:py-6 px-3 md:px-4">
				<PaymentStatus
					message="Ticket booked successfully. You will receive an email with your ticket(s) details."
					title="Ticket Booking"
					returnUrl="/vmms/events"
					urlName="Events"
				/>
			</div>
		</div>
	</div>
</template>
<script setup>
import { Breadcrumbs, createResource, Button, ErrorMessage } from "frappe-ui";
import { attendeeBooking } from "../utils/booking";
import TicketCard from "../components/TicketCard.vue";
import { ref } from "vue";
import { toast } from "frappe-ui";
import { paymentListener } from "../utils/payment";
import PaymentStatus from "../components/PaymentStatus.vue";
import EmptyState from "../components/EmptyState.vue";
import { registrationResponses } from "../composables/RegistrationQuestions";

const checkSTK = ref(false);
const invoice = ref("");
const eventBooking = ref("");
const paymentStatus = ref(false);
const { formResponse, clearResponses } = registrationResponses();

const ticketType = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.get_event_ticket_type",
	makeParams() {
		return {
			ticket_id: attendeeBooking.getBookingData().ticketDetails.ticket_type,
		};
	},
	auto: true,
});

function proceedToPay() {
	handlePay.submit({});
}

const handlePay = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.handle_ticket_payment",
	makeParams() {
		return {
			payload: {
				event_name: ticketType.data.event_details?.name,
				ticket_name: ticketType.data.name,
				booking_details: attendeeBooking.getBookingData().attendees,
				registration_responses: formResponse.value,
			},
		};
	},
	onSuccess(data) {
		if (data) {
			checkSTK.value = true;
			toast.success(
				"Payment initiated successfully. Please complete the payment on your phone."
			);
			invoice.value = data.invoice;
			eventBooking.value = data.event_booking;
			confirmPaymentStatus.loading = true;
			clearResponses();
			initiatePaymentListener(data);
		}
	},
	onError() {
		handlePay.error = "An error occurred during payment. Please try again.";
	},
});

function initiatePaymentListener(data) {
	const paymentInstance = paymentListener;
	paymentInstance.saveToken(data.payment_token);
	paymentInstance.listenForPayment(data.payment_token).then((status) => {
		confirmPaymentStatus.loading = false;

		if (status === "Completed") {
			paymentStatus.value = true;
			attendeeBooking.clearBookingData();
			toast.success("Payment successful! Your ticket has been booked.");
		} else if (status === "Timeout") {
			checkSTK.value = false;
			handlePay.error =
				"We haven't received confirmation for this payment yet. If you completed it on your phone, please check your bookings in a moment before paying again.";
		} else {
			checkSTK.value = false;
			handlePay.error = "There was an error processing your payment. Please try again.";
		}
	});
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
</script>
