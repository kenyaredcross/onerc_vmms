<template>
  <Dialog v-model="setAvailability" :options="{ size: '5xl' }">
    <template #body-title>
      <h3 class="text-xl font-bold text-gray-900">
        Set Your Weekly Availability
      </h3>
    </template>
    <template #body-content>
      <div class="p-4 bg-red-50 rounded-lg mb-6">
        <p class="text-red-700">
          Select the shifts you're available for each day of the week. This will
          be your ongoing weekly availability pattern.
        </p>
      </div>

      <!-- Availability Table -->
      <div class="overflow-x-auto">
        <table class="w-full border-collapse border">
          <thead>
            <tr>
              <th class="border p-3 text-left font-bold">Days/Shifts</th>
              <th
                v-for="shift in shifts.data"
                :key="shift.name"
                class="border p-3 text-center font-bold"
              >
                <div>
                  <div class="font-bold">{{ shift.name }}</div>
                  <div class="text-xs font-normal">
                    {{ formatTime(shift.start_time) }} -
                    {{ formatTime(shift.end_time) }}
                  </div>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="day in daysList" :key="day.value">
              <td class="border p-3">
                <div class="font-semibold">{{ day.label }}</div>
              </td>
              <td
                v-for="shift in shifts.data"
                :key="`${day.value}-${shift.name}`"
                class="border p-3 text-center"
              >
                <input
                  type="checkbox"
                  :id="`${day.value}-${shift.name}`"
                  v-model="availability[day.value]"
                  :value="shift.name"
                  class="w-6 h-6 focus:ring-red-500 text-red-600 rounded"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Quick Actions -->
      <div class="mt-4 flex flex-wrap gap-2">
        <Button variant="outline" theme="red" @click="selectAllShifts">
          Select All
        </Button>
        <Button variant="outline" theme="red" @click="clearAllShifts">
          Clear All
        </Button>
      </div>
    </template>
    <template #actions>
      <div class="flex flex-row justify-end space-x-2 w-full items-center">
        <Button variant="outline" theme="gray" @click="cancel"> Close </Button>
        <Button
          variant="solid"
          theme="green"
          :loading="newSlot.loading"
          @click="submitAvailability"
          :disabled="totalSelectedShifts === 0"
        >
          Save
        </Button>
      </div>
      <ErrorMessage :message="newSlot.error" class="mt-2 text-center" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import {
  Dialog,
  Button,
  createResource,
  ErrorMessage,
  createListResource,
} from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import { usersStore } from "../../stores/user";

const { roleResource, presentSlots } = usersStore();
const setAvailability = ref(true);

const emit = defineEmits(["success", "cancel"]);

const shifts = createListResource({
  doctype: "Shift Type",
  fields: ["name", "start_time", "end_time"],
  auto: true,
  orderBy: "start_time asc",
  cache: ["shifts"],
});

const daysList = [
  { label: "Monday", value: "Monday" },
  { label: "Tuesday", value: "Tuesday" },
  { label: "Wednesday", value: "Wednesday" },
  { label: "Thursday", value: "Thursday" },
  { label: "Friday", value: "Friday" },
  { label: "Saturday", value: "Saturday" },
  { label: "Sunday", value: "Sunday" },
];

const availability = reactive({
  Monday: [],
  Tuesday: [],
  Wednesday: [],
  Thursday: [],
  Friday: [],
  Saturday: [],
  Sunday: [],
});

const newSlot = createResource({
  url: "non_profit.non_profit.api.create_availability_schedule",
  makeParams(values) {
    return { slot_data: { ...values } };
  },
  onSuccess() {
    availabilitySlots.reload();
    emit("success");
    presentSlots.reload();
    setAvailability.value = false;
  },
});

function formatTime(timeString) {
  if (!timeString) return "";
  const time = timeString.split(":");
  const hours = parseInt(time[0]);
  const minutes = time[1];
  const ampm = hours >= 12 ? "PM" : "AM";
  const displayHours = hours % 12 || 12;
  return `${displayHours}:${minutes} ${ampm}`;
}

function capitalizeDay(day) {
  return day.charAt(0).toUpperCase() + day.slice(1);
}

const availabilitySlots = createResource({
  url: "non_profit.non_profit.api.get_availability_slots",
  auto: true,
  onSuccess(data) {
    if (data && Array.isArray(data) && data.length > 0) {
      data.forEach((slot) => {
        const day = slot.day.toLowerCase();
        const shiftType = slot.shift_type;

        if (availability[day] && Array.isArray(availability[day])) {
          if (!availability[day].includes(shiftType)) {
            availability[day].push(shiftType);
          }
        }
      });
    } else {
      resetForm();
    }
  },
});

function cancel() {
  setAvailability.value = false;
  emit("cancel");
}

function resetForm() {
  availability.Monday = [];
  availability.Tuesday = [];
  availability.Wednesday = [];
  availability.Thursday = [];
  availability.Friday = [];
  availability.Saturday = [];
  availability.Sunday = [];
  newSlot.error = "";
}

function selectAllShifts() {
  const allShifts = shifts.data?.map((shift) => shift.name) || [];
  Object.keys(availability).forEach((day) => {
    availability[day] = [...allShifts];
  });
}

function clearAllShifts() {
  resetForm();
}

function submitAvailability() {
  newSlot.error = "";

  if (totalSelectedShifts.value === 0) {
    newSlot.error = "Please select at least one shift";
    return;
  }

  const slotData = {
    employee: roleResource.data.employee,
    weekly_availability: { ...availability },
  };

  newSlot.submit(slotData);
}

const totalSelectedShifts = computed(() => {
  return Object.values(availability).reduce(
    (total, dayShifts) => total + dayShifts.length,
    0
  );
});
</script>
