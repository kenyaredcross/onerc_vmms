<template>
	<SettingsHeader class="!px-4 !pt-6 sm:!px-[4.4rem] sm:!pt-10">
		<div class="flex items-start justify-between gap-4">
			<div class="flex min-w-0 flex-col gap-1">
				<h2 class="text-lg font-semibold text-ink-gray-8">{{ __("Availability") }}</h2>
				<p class="text-base text-ink-gray-6">
					{{ __("Set the shifts you can be deployed on each week.") }}
				</p>
			</div>
			<Badge v-if="totalSelectedShifts" theme="red" variant="subtle" class="shrink-0">
				{{ totalSelectedShifts }}
			</Badge>
		</div>
	</SettingsHeader>

	<PanelBody>
		<div class="flex flex-col gap-6">
			<div class="mt-2 rounded-lg bg-surface-red-1 px-3 py-2">
				<p class="text-sm text-ink-red-8">
					{{
						__(
							"Select the shifts you're available for each day of the week. This will be your ongoing weekly availability pattern."
						)
					}}
				</p>
			</div>

			<div class="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
				<table class="w-full min-w-[20rem] border-collapse">
					<thead>
						<tr>
							<th
								scope="col"
								class="sticky left-0 z-10 border border-outline-gray-2 bg-surface-gray-1 p-2 text-left text-sm-medium text-ink-gray-7"
							>
								{{ __("Day") }}
							</th>
							<th
								v-for="shift in shifts.data"
								:key="shift.name"
								scope="col"
								class="border border-outline-gray-2 bg-surface-gray-1 p-2 text-center text-sm-medium text-ink-gray-7"
							>
								<div class="whitespace-nowrap">{{ shift.name }}</div>
								<div class="text-xs font-normal text-ink-gray-5 whitespace-nowrap">
									{{ formatTime(shift.start_time) }} -
									{{ formatTime(shift.end_time) }}
								</div>
							</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="day in daysList" :key="day.value">
							<th
								scope="row"
								class="sticky left-0 z-10 border border-outline-gray-2 bg-surface-base p-2 text-left text-sm-medium text-ink-gray-8 whitespace-nowrap"
							>
								{{ __(day.label) }}
							</th>
							<td
								v-for="shift in shifts.data"
								:key="`${day.value}-${shift.name}`"
								class="border border-outline-gray-2 p-2 text-center"
							>
								<Checkbox
									:id="`${day.value}-${shift.name}`"
									:modelValue="availability[day.value].includes(shift.name)"
									:aria-label="`${day.label} ${shift.name}`"
									class="justify-center"
									@update:modelValue="toggleShift(day.value, shift.name)"
								/>
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<SettingsRow
				:title="__('Available on Holidays')"
				:description="__('Include public holidays in your weekly pattern.')"
			>
				<Switch v-model="availableOnHolidays" />
			</SettingsRow>

			<div
				class="flex flex-col gap-3 border-t border-outline-gray-2 pt-4 sm:flex-row sm:items-center sm:justify-between"
			>
				<div class="flex flex-wrap gap-2">
					<Button variant="subtle" theme="red" @click="selectAllShifts">
						{{ __("Select All") }}
					</Button>
					<Button variant="subtle" theme="gray" @click="clearAllShifts">
						{{ __("Clear All") }}
					</Button>
				</div>
				<Button
					variant="solid"
					theme="red"
					class="w-full sm:w-auto"
					:loading="newSlot.loading"
					:disabled="totalSelectedShifts === 0 && !availableOnHolidays"
					@click="submitAvailability"
				>
					{{ __("Save") }}
				</Button>
			</div>
			<ErrorMessage :message="newSlot.error" />
		</div>
	</PanelBody>
</template>

<script setup lang="ts">
import {
	Badge,
	Button,
	Checkbox,
	createListResource,
	createResource,
	ErrorMessage,
	SettingsHeader,
	SettingsRow,
	Switch,
} from "frappe-ui";
import { computed, reactive, ref } from "vue";
import { usersStore } from "../../stores/user";
import PanelBody from "./PanelBody.vue";

interface ShiftType {
	name: string;
	start_time: string;
	end_time: string;
}

interface AvailabilityData {
	[key: string]: string[];
}

interface AvailabilityResponse {
	schedules: {
		day: string;
		shift_type: string;
	}[];
	available_on_holidays: boolean;
}

const { roleResource, presentSlots } = usersStore();
const availableOnHolidays = ref<boolean>(false);

const shifts = createListResource<ShiftType[]>({
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

const availability = reactive<AvailabilityData>({
	Monday: [],
	Tuesday: [],
	Wednesday: [],
	Thursday: [],
	Friday: [],
	Saturday: [],
	Sunday: [],
});

const newSlot = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.volunteer.create_availability_schedule",
	makeParams(values: Record<string, any>) {
		return { slot_data: { ...values } };
	},
	onSuccess() {
		availabilitySlots.reload();
		presentSlots.reload();
	},
});

function formatTime(timeString: string): string {
	if (!timeString) return "";
	const [hour, minute] = timeString.split(":");
	const hours = parseInt(hour);
	const ampm = hours >= 12 ? "PM" : "AM";
	const displayHours = hours % 12 || 12;
	return `${displayHours}:${minute} ${ampm}`;
}

function capitalizeDay(day: string): string {
	return day.charAt(0).toUpperCase() + day.slice(1);
}

const availabilitySlots = createResource<AvailabilityResponse>({
	url: "onerc_vmms.volunteer_and_member_management.api.volunteer.get_availability_slots",
	auto: true,
	onSuccess(data) {
		resetForm();
		if (data?.schedules?.length) {
			data.schedules.forEach((slot) => {
				const day = capitalizeDay(slot.day.trim().toLowerCase());
				const shiftType = slot.shift_type?.trim();
				if (availability[day] && Array.isArray(availability[day])) {
					if (!availability[day].includes(shiftType)) {
						availability[day].push(shiftType);
					}
				}
			});
		}
		availableOnHolidays.value = !!data?.available_on_holidays;
	},
});

function toggleShift(day: string, shiftName: string) {
	const index = availability[day].indexOf(shiftName);
	if (index === -1) {
		availability[day].push(shiftName);
	} else {
		availability[day].splice(index, 1);
	}
}

function resetForm() {
	Object.keys(availability).forEach((day) => {
		availability[day] = [];
	});
	availableOnHolidays.value = false;
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
	if (totalSelectedShifts.value === 0 && !availableOnHolidays.value) {
		newSlot.error = "Please select at least one shift or enable holiday availability";
		return;
	}
	const slotData = {
		employee: roleResource.data.employee,
		weekly_availability: { ...availability },
		available_on_holidays: availableOnHolidays.value,
	};
	newSlot.submit(slotData);
}

const totalSelectedShifts = computed<number>(() => {
	return Object.values(availability).reduce((total, dayShifts) => total + dayShifts.length, 0);
});
</script>
