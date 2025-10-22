<template>
  <div class="max-w-7xl mx-auto md:px-4 px-2 lg:px-8 py-10">
    <h3
      class="text-2xl md:text-3xl font-extrabold text-gray-800 mb-8 text-center md:text-left"
    >
      🎟️ My Tickets
    </h3>

    <div
      v-if="tickets && tickets.length"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8"
    >
      <div
        v-for="ticket in tickets"
        :key="ticket.name"
        class="relative group bg-gradient-to-br from-white via-gray-50 to-gray-100 border border-gray-200 rounded-2xl shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col items-center text-center"
      >
        <div
          class="absolute -top-1 -right-1 w-16 h-16 bg-gradient-to-br from-red-400 to-pink-500 rounded-full blur-lg opacity-10 group-hover:opacity-20 transition-opacity"
        ></div>

        <div
          class="text-lg font-semibold text-gray-800 mb-1 bg-gradient-to-r from-red-500 to-pink-500 text-transparent bg-clip-text"
        >
          {{ ticket?.ticket_type_title || "General Ticket" }}
        </div>

        <div class="w-12 h-1 bg-red-100 rounded-full my-2"></div>
        <div
          v-if="ticket.qr_code"
          class="mb-4 flex justify-center items-center w-32 h-32 bg-white border border-gray-100 rounded-xl shadow-inner"
        >
          <img
            :src="ticket.qr_code"
            alt="QR Code"
            class="w-28 h-28 object-contain"
          />
        </div>

        <div
          class="mt-6 w-full border-t border-dashed border-gray-300 relative"
        >
          <div
            class="absolute -top-3 -left-3 w-6 h-6 bg-gray-50 border border-gray-300 rounded-full"
          ></div>
          <div
            class="absolute -top-3 -right-3 w-6 h-6 bg-gray-50 border border-gray-300 rounded-full"
          ></div>
        </div>

        <div class="space-y-1 text-sm text-gray-700 mt-4">
          <p>
            <span class="font-medium text-gray-500">Name:</span>
            {{ ticket.attendee_name }}
          </p>
          <p>
            <span class="font-medium text-gray-500">Email:</span>
            {{ ticket.attendee_email }}
          </p>
        </div>
      </div>
    </div>

    <div
      v-else
      class="text-gray-500 text-center py-16 bg-white border border-gray-100 rounded-2xl shadow-sm"
    >
      <p class="text-lg font-medium mb-2">No booked tickets found</p>
      <p class="text-sm text-gray-400">
        Once you register for an event, your tickets will appear here.
      </p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tickets: {
    type: Array,
    default: () => [],
  },
});
</script>
