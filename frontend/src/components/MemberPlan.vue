<template>
	<div class="flex flex-col lg:flex-row gap-10 md:gap-12 px-4 md:px-8 py-6 bg-gray-50 max-w-6xl">
		<div class="flex-1 space-y-2 md:space-y-6">
			<h1 class="text-lg md:text-3xl text-gray-900">Your Membership(s)</h1>

			<div v-if="membershipList.data && membershipList.data.length > 0" class="space-y-5">
				<div
					v-for="membership in membershipList.data"
					:key="membership.name"
					class="group relative rounded-2xl bg-white border border-gray-200 hover:shadow-lg transition-all duration-300 p-6"
				>
					<div
						class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6"
					>
						<div class="flex items-center gap-5 flex-1">
							<div
								class="w-3 h-3 rounded-full"
								:class="{
									'bg-green-500': membership.status === 'Active',
									'bg-red-500': membership.status === 'Expired',
									'bg-yellow-500': membership.status === 'Pending',
								}"
							></div>
							<div>
								<h3 class="text-lg font-semibold text-gray-900">
									{{ membership.membership_type }}
								</h3>
								<p class="text-sm text-gray-700">
									{{ membership.company }}
								</p>
							</div>
						</div>

						<div class="flex gap-8 justify-between sm:justify-start text-gray-800">
							<div>
								<p
									class="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1"
								>
									Started
								</p>
								<p class="text-sm font-semibold">
									{{ formatDate(membership.from_date) }}
								</p>
							</div>
							<div>
								<p
									class="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1"
								>
									Renewal
								</p>
								<p class="text-sm font-semibold">
									{{ formatDate(membership.to_date) }}
								</p>
							</div>
						</div>

						<div class="flex items-center justify-end gap-5">
							<div class="text-right">
								<div class="text-2xl font-bold text-gray-900">
									{{ membership.amount }}
								</div>
								<div class="text-xs text-gray-700">KES</div>
							</div>
							<Button
								variant="solid"
								theme="red"
								size="sm"
								class="rounded-lg px-5 py-2"
								:loading="loadCertificate === membership.name"
								@click="
									openRenewDialog(
										membership.status,
										membership.name,
										membership.membership_type,
									)
								"
							>
								{{
									membership.status === "Active" ? "Print Certificate" : "Renew"
								}}
							</Button>
						</div>
					</div>
					<ErrorMessage :message="certificate.error" class="text-center mt-2" />
				</div>
			</div>

			<div v-else class="text-center text-gray-700">No memberships found.</div>
		</div>

		<aside
			v-if="
				membershipList.data &&
				membershipList.data.length > 0 &&
				roleResource.data &&
				!roleResource.data.is_volunteer
			"
			class="w-full lg:w-1/3 flex-shrink-0"
		>
			<div
				class="relative rounded-2xl bg-gradient-to-br from-red-600 to-red-700 p-8 text-white overflow-hidden shadow-md"
			>
				<div
					class="absolute top-0 right-0 w-56 h-56 bg-white opacity-10 rounded-full -mr-28 -mt-28"
				></div>
				<div
					class="absolute bottom-0 left-0 w-48 h-48 bg-white opacity-10 rounded-full -ml-24 -mb-24"
				></div>

				<div class="relative flex flex-col gap-5">
					<div>
						<h2 class="text-2xl font-bold mb-2">Become a Volunteer</h2>
						<p class="text-red-50 leading-relaxed opacity-90 text-sm">
							Join Kenya Red Cross Society and support your community through
							life-saving services while gaining valuable skills.
						</p>
					</div>

					<RouterLink :to="{ name: 'VolunteerSignup' }" class="block mt-4">
						<Button
							variant="solid"
							class="w-full bg-white text-red-600 hover:bg-gray-100 rounded-lg font-semibold h-12"
							icon-right="arrow-right"
						>
							Register Now
						</Button>
					</RouterLink>
				</div>
			</div>
		</aside>
	</div>

	<Dialog v-model="payNow">
		<template #body-title>
			<h3 class="text-2xl font-bold text-gray-900">Renew Membership</h3>
		</template>

		<template #body-content>
			<form @submit.prevent="payMembership" class="space-y-5">
				<div>
					<label class="block text-sm font-medium text-gray-800 mb-2">
						M-Pesa Phone Number
					</label>
					<Input
						required
						:type="'text'"
						size="md"
						variant="subtle"
						:disabled="renewMembership.loading"
						placeholder="+254 712 345 678"
						v-model="phoneNumber"
					/>
				</div>
				<ErrorMessage v-if="errorMessage" :message="errorMessage" />
				<Button
					type="button"
					variant="solid"
					theme="red"
					class="w-full rounded-lg h-12"
					@click="payMembership"
					:loading="renewMembership.loading"
				>
					Pay Now
				</Button>
			</form>
		</template>
	</Dialog>
</template>

<script lang="ts" setup>
import { Button, createResource, Dialog, ErrorMessage, Input, toast } from "frappe-ui";
import { ref } from "vue";
import { RouterLink } from "vue-router";
import { usersStore } from "../stores/user";
import { isValidPhone } from "../utils/volunteer";

const { roleResource } = usersStore();

const payNow = ref(false);
const phoneNumber = ref("");
const errorMessage = ref("");
const selectedMembershipId = ref<string | undefined>(undefined);
const loadCertificate = ref<string | null>(null);

interface Membership {
	name?: string;
	membership_type?: string;
	from_date?: string;
	to_date?: string;
	status?: string;
	amount?: number;
	company?: string;
	type_details?: Record<string, any>;
}

const membershipTypeCert = ref("");
const membershipList = createResource<Membership[]>({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.get_current_membership",
	auto: true,
	cache: ["currentMembership"],
});

const renewMembership = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.renew_membership",
	makeParams() {
		return {
			id: selectedMembershipId.value,
			phone_number: phoneNumber.value,
		};
	},
	onSuccess() {
		toast.success("Payment initiated successfully! Check your phone for a prompt.");
		payNow.value = false;
		phoneNumber.value = "";
		selectedMembershipId.value = undefined;
		membershipList.reload();
	},
	onError(error: any) {
		errorMessage.value = error.message || "Failed to initiate membership renewal.";
	},
});

function formatDate(dateStr?: string): string {
	if (!dateStr) return "";
	const date = new Date(dateStr);
	return date.toLocaleDateString("en-GB", {
		day: "2-digit",
		month: "short",
		year: "numeric",
	});
}

const certificate = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.membership_certificate_template",
	makeParams() {
		return {
			membership_type: membershipTypeCert.value,
		};
	},
});

function openRenewDialog(
	membershipStatus?: string,
	membershipId?: string,
	membershipType?: string,
) {
	if (membershipStatus === "Active") {
		membershipTypeCert.value = membershipType || "";

		getCertificate(membershipId);

		return;
	}

	if (membershipId) {
		selectedMembershipId.value = membershipId;
		errorMessage.value = "";
		payNow.value = true;
	}
}

function getCertificate(membershipId?: string) {
	loadCertificate.value = membershipId || null;
	certificate.submit(
		{},
		{
			onSuccess() {
				loadCertificate.value = null;
				window.open(
					`/api/method/frappe.utils.print_format.download_pdf?doctype=Membership&name=${membershipId}&format=${membershipTypeCert.value}`,
					"_blank",
				);
			},
		},
	);
}

function payMembership() {
	if (!phoneNumber.value) {
		errorMessage.value = "Please enter your phone number";
		return;
	}

	if (!isValidPhone(phoneNumber.value)) {
		errorMessage.value = "Please enter a valid Kenyan phone number. eg. (+254123456789)";
		return;
	}

	if (!selectedMembershipId.value) {
		errorMessage.value = "Error: Membership ID is missing.";
		return;
	}

	errorMessage.value = "";
	renewMembership.submit({
		membership: selectedMembershipId.value,
		phone_number: phoneNumber.value,
	});
}
</script>
