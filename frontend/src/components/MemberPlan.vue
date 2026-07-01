<template>
	<div
		class="flex flex-col lg:flex-row gap-10 md:gap-12 px-4 md:px-8 md:py-6 bg-surface-gray rounded-2xl border border-outline-gray-2 max-w-6xl"
	>
		<div class="flex-1 py-2 md:space-y-6">
			<h1 class="my-1 md:text-3xl text-ink-gray-8">{{ __("Your Membership(s)") }}</h1>

			<div v-if="membershipList.data && membershipList.data.length > 0" class="space-y-5">
				<div
					v-for="membership in membershipList.data"
					:key="membership.name"
					class="group relative rounded-2xl bg-surface-white border border-outline-gray-2 hover:shadow-lg transition-all duration-300 p-6"
				>
					<div
						class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6"
					>
						<div class="flex items-center gap-5 flex-1">
							<Badge
								variant="outline"
								:theme="
									membership.status === 'Active'
										? 'green'
										: membership.status === 'Pending'
										? 'orange'
										: 'red'
								"
							>
								{{ __(membership.status) }}
							</Badge>
							<div>
								<h3 class="text-lg font-semibold text-ink-gray-1-900">
									{{ __(membership.membership_type) }}
								</h3>
								<p class="text-sm text-ink-gray-1-700">
									{{ __(membership.company) }}
								</p>
							</div>
						</div>

						<div
							class="flex gap-8 justify-between sm:justify-start text-ink-gray-1-800"
						>
							<div>
								<p
									class="text-xs text-ink-gray-1-500 uppercase tracking-wide font-medium mb-1"
								>
									{{ __("Started") }}
								</p>
								<p class="text-sm font-semibold">
									{{ __(formatDate(membership.from_date)) }}
								</p>
							</div>
							<div v-if="membership.type_details?.billing_cycle !== 'One Off'">
								<p
									class="text-xs text-ink-gray-1-500 uppercase tracking-wide font-medium mb-1"
								>
									{{ __("Renewal") }}
								</p>
								<p class="text-sm font-semibold">
									{{ __(formatDate(membership.to_date)) }}
								</p>
							</div>
						</div>

						<div class="flex items-center justify-end gap-5">
							<div class="text-right">
								<div class="text-2xl font-bold text-ink-gray-1-900">
									{{ __(membership.amount) }}
								</div>
								<div class="text-xs text-ink-gray-1-700">{{ __("KES") }}</div>
							</div>
							<Button
								v-if="
									membership.status === 'Active' ||
									membership.status === 'Expired'
								"
								variant="solid"
								theme="red"
								size="sm"
								class="rounded-lg px-5 py-2"
								:loading="loadCertificate === membership.name"
								@click="openRenewDialog(membership)"
							>
								{{
									membership.status === "Active" ||
									membership.type_details?.billing_cycle === "One Off"
										? __("Print Certificate")
										: __("Renew ")
								}}
							</Button>
							<Popover v-else trigger="hover" :hoverDelay="0.5">
								<template #target>
									<Button variant="outline" theme="red">{{
										__("Under Review")
									}}</Button>
								</template>
								<template #body-main>
									<div class="text-sm p-2 text-ink-gray-9">
										{{ __("We're reviewing your application.") }}
										<br />
										{{ __("You'll be notified when approved.") }}
										<br />
									</div>
								</template>
							</Popover>
						</div>
					</div>
					<ErrorMessage :message="certificate.error" class="text-center mt-2" />
				</div>
			</div>

			<div v-else class="text-center text-ink-gray-1-700">
				{{ __("No memberships found.") }}
			</div>
		</div>

		<aside
			v-if="
				membershipList.data &&
				membershipList.data.length > 0 &&
				roleResource.data &&
				!roleResource.data.is_pending_approval &&
				!roleResource.data.is_volunteer
			"
			class="w-full lg:w-1/3 flex-shrink-0"
		>
			<div
				class="relative rounded-2xl bg-gradient-to-br from-red-600 to-red-700 p-8 text-white overflow-hidden shadow-md"
			>
				<div
					class="absolute top-0 right-0 w-56 h-56 bg-surface-white opacity-10 rounded-full -mr-28 -mt-28"
				></div>
				<div
					class="absolute bottom-0 left-0 w-48 h-48 bg-surface-white opacity-10 rounded-full -ml-24 -mb-24"
				></div>

				<div class="relative flex flex-col gap-5">
					<div>
						<h2 class="text-2xl font-bold mb-2">{{ __("Become a Volunteer") }}</h2>
						<p class="text-red-50 leading-relaxed opacity-90 text-sm">
							{{
								__(
									"Join Kenya Red Cross Society and support your community through life-saving services while gaining valuable skills."
								)
							}}
						</p>
					</div>

					<RouterLink :to="{ name: 'VolunteerSignup' }" class="block mt-4">
						<Button
							variant="solid"
							class="w-full bg-surface-white text-red-600 hover:bg-surface-gray-100 rounded-lg font-semibold h-12"
							icon-right="arrow-right"
						>
							{{
								roleResource.data.vol_applicant
									? __("Continue with Volunteer Registration")
									: __("Register Now")
							}}
						</Button>
					</RouterLink>
				</div>
			</div>
		</aside>
	</div>

	<RegisterMembership
		v-model="renew"
		:is_renew="true"
		:membership_type="selectedMembership.membership_type"
		:amount="selectedMembership.amount"
		:renew_branch="selectedMembership.company"
	/>
</template>

<script lang="ts" setup>
import { Badge, Button, createResource, ErrorMessage, Popover } from "frappe-ui";
import { reactive, ref } from "vue";
import { RouterLink } from "vue-router";
import { usersStore } from "../stores/user";
import RegisterMembership from "./Modals/RegisterMembership.vue";

const { roleResource } = usersStore();

const renew = ref(false);
const errorMessage = ref("");
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

const selectedMembership = reactive({
	name: "",
	membership_type: "",
	amount: 0,
	company: "",
});

const membershipTypeCert = ref("");
const membershipList = createResource<Membership[]>({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.get_current_membership",
	auto: true,
	cache: ["currentMembership"],
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

function openRenewDialog(membership: Membership) {
	if (membership.status === "Active") {
		membershipTypeCert.value = membership.membership_type || "";

		getCertificate(membership.name);

		return;
	}

	if (membership.name) {
		selectedMembership.name = membership.name;
		selectedMembership.membership_type = membership.membership_type || "";
		selectedMembership.amount = membership.amount || 0;
		selectedMembership.company = membership.company || "";
		errorMessage.value = "";
		renew.value = true;
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
					`/api/method/onerc_vmms.volunteer_and_member_management.utils.download_pdf?doctype=VM Membership&name=${membershipId}&format=${membershipTypeCert.value}`,
					"_blank"
				);
			},
		}
	);
}
</script>
