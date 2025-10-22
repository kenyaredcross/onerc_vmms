<template>
  <Dialog v-model="isOpen">
    <template #body-title>
      <div class="space-y-2">
        <h3 class="text-2xl font-bold text-gray-900">Select Your Ticket</h3>
        <p class="text-sm text-gray-500">
          Choose the perfect ticket for your experience
        </p>
      </div>
    </template>

    <template #body-content>
      <div class="mt-6 space-y-3">
        <div
          v-for="ticket in props.tickets"
          :key="ticket.id"
          class="group relative overflow-hidden p-5 border-2 rounded-2xl bg-white cursor-pointer transition-all duration-300"
          :class="{
            'border-red-500 shadow-md shadow-red-100':
              selectedTicket === ticket.name,
            'border-gray-100 hover:border-red-300':
              selectedTicket !== ticket.name,
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
                <svg
                  class="w-5 h-5 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 5l7 7-7 7"
                  />
                </svg>
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
          v-model="amount"
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
          placeholder="First Name"
          label="First Name"
          v-model="ticketData.first_name"
        />
        <Input
          v-if="user.data === 'Guest'"
          required
          name="last_name"
          type="text"
          placeholder="Last Name"
          label="Last Name"
          v-model="ticketData.last_name"
        />
        <Input
          required
          name="phone"
          type="text"
          placeholder="0712345678"
          label="Phone"
          v-model="ticketData.phone"
        />
      </div>

      <ErrorMessage
        v-if="handlePay.error"
        :message="handlePay.error"
        class="text-center border border-red-400 rounded-md p-2 mt-3"
      />

      <Button
        v-if="payStatus"
        class="w-full mt-4"
        theme="green"
        variant="solid"
        @click="proceedToPay"
        :loading="handlePay.loading"
      >
        {{ handlePay.loading ? "Processing Payment" : "Proceed to Pay" }}
      </Button>
    </template>
  </Dialog>
</template>

<script setup>
import { Dialog, Button, Input, createResource, ErrorMessage } from "frappe-ui";
import { computed, inject, reactive, ref } from "vue";
const isOpen = ref(false);
const payStatus = ref(false);
const amount = computed(() => {
  return `${ticketData.currency} ${ticketData.price}`;
});
const selectedTicket = ref(null);
const user = inject("$user");

const ticketData = reactive({
  ticket_type: "",
  price: "",
  currency: "",
  phone: "",
  ticket_name: "",
  email: "",
  first_name: "",
  last_name: "",
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

function handleSelection(ticket) {
  selectedTicket.value = ticket.name;
  payStatus.value = true;
  ticketData.ticket_type = ticket.title;
  ticketData.price = ticket.price;
  ticketData.currency = ticket.currency;
  ticketData.ticket_name = ticket.name;
}

const handlePay = createResource({
  url: "non_profit.non_profit.api.handle_ticket_payment",
  makeParams() {
    return {
      event_name: props.event,
      phone: ticketData.phone,
      ticket_name: ticketData.ticket_name,
      email: ticketData.email,
      first_name: ticketData.first_name,
      last_name: ticketData.last_name,
    };
  },
  onSuccess(data) {
    if (data.success) {
      if (data.tickets && data.tickets.length > 0) {
        const firstTicket = data.tickets[0];
        if (firstTicket.qr_code) {
          window.location.href = firstTicket.qr_code;
          return;
        }
      }

      isOpen.value = false;
      window.location.reload();
    } else {
      handlePay.error = data.message || "Payment failed. Please try again.";
    }
  },
  onError(error) {
    handlePay.error = error.message || "An error occurred. Please try again.";
  },
});

function validatePhone(phone) {
  const phoneRegex = /^07\d{8}$/;
  return phoneRegex.test(phone);
}

function proceedToPay() {
  if (user.data == "Guest") {
    if (
      !ticketData.email ||
      !ticketData.first_name ||
      !ticketData.last_name ||
      !ticketData.phone
    ) {
      handlePay.error = "All fields are required";
      return;
    }
  } else {
    if (!ticketData.phone) {
      handlePay.error = "Phone number is required";
      return;
    }

    if (!validatePhone(ticketData.phone)) {
      handlePay.error =
        "Invalid phone number format. Please use 0712345678 format";
      return;
    }
  }
  handlePay.submit({});
}
</script>
