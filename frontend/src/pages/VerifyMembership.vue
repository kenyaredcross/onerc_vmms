<template>
	<div class="flex min-h-screen bg-surface-base">
		<div
			class="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-red-600 via-red-700 to-red-900 p-12 text-white lg:flex"
		>
			<div class="absolute -top-24 -left-24 h-96 w-96 rounded-full bg-white/10 blur-3xl" />
			<div
				class="absolute -bottom-32 -right-16 h-[28rem] w-[28rem] rounded-full bg-black/20 blur-3xl"
			/>
			<div
				class="absolute top-1/3 right-10 h-40 w-40 rounded-3xl border border-white/10 rotate-12"
			/>
			<div
				class="absolute bottom-24 left-16 h-24 w-24 rounded-2xl border border-white/10 -rotate-6"
			/>

			<div class="relative flex items-center gap-3">
				<img
					:src="vmmsLogo"
					:alt="brandName"
					class="h-12 w-12 rounded-xl object-contain shadow-lg"
				/>
				<span class="text-2xl-semibold tracking-wide">
					<Button icon-right="arrow-right" class="border">
						Visit <RouterLink to="/">{{ __(brandName || "VMMS") }}</RouterLink></Button
					>
				</span>
			</div>

			<div class="relative max-w-md">
				<p class="text-sm-medium uppercase tracking-[0.2em] text-red-200">
					{{ __("Membership Verification") }}
				</p>
				<h1 class="mt-3 text-5xl-bold leading-tight">
					{{ __("One scan.") }}<br />
					{{ __("Verified in real time.") }}
				</h1>
				<p class="mt-4 text-red-100">
					{{
						__(
							"Every membership card carries a digitally signed QR code. What you see here is fetched live from our records at the moment of scanning."
						)
					}}
				</p>

				<ul class="mt-8 space-y-3 text-sm text-red-50">
					<li v-for="point in trustPoints" :key="point" class="flex items-center gap-3">
						<span
							class="flex h-6 w-6 items-center justify-center rounded-full bg-white/15"
						>
							<FeatherIcon name="check" class="h-3.5 w-3.5" />
						</span>
						{{ point }}
					</li>
				</ul>
			</div>

			<p class="relative text-xs text-red-200">
				{{ __("Verified live at scan time by") }} {{ __(brandName) }}
			</p>
		</div>

		<div
			class="flex w-full flex-col items-center justify-center px-4 py-10 lg:w-1/2 bg-surface-gray-1"
		>
			<div class="mb-8 flex items-center gap-3 lg:hidden">
				<img
					:src="brandLogo"
					:alt="brandName"
					class="h-10 w-10 rounded-lg object-contain"
				/>
				<span class="text-lg-semibold text-ink-gray-9">{{ __(brandName) }}</span>
				<Button><RouterLink to="/"></RouterLink></Button>
			</div>

			<div class="w-full max-w-md" :aria-busy="verification.loading">
				<div v-if="verification.loading" class="flex flex-col items-center gap-3 py-20">
					<ProgressSpinner :message="'Verifying Membership'" />
				</div>

				<div
					v-else-if="verification.error"
					class="overflow-hidden rounded-2xl border border-outline-gray-2 bg-surface-base shadow-sm"
				>
					<div class="bg-red-700 px-6 py-8 text-center text-white">
						<FeatherIcon name="x-circle" class="mx-auto h-12 w-12" />
						<p class="mt-3 text-2xl-semibold">
							{{ __("Invalid Verification Link") }}
						</p>
					</div>
					<p class="px-6 py-6 text-center text-sm text-ink-gray-6">
						{{
							__(
								"This QR code or link could not be verified. Please scan the QR code on the membership card again, or contact support."
							)
						}}
					</p>
				</div>

				<div
					v-else-if="verification.data"
					class="overflow-hidden rounded-2xl border border-outline-gray-2 bg-surface-base shadow-sm"
				>
					<div
						class="px-6 py-8 text-center text-white"
						:class="verification.data.is_valid ? 'bg-green-600' : 'bg-red-700'"
					>
						<FeatherIcon
							:name="verification.data.is_valid ? 'check-circle' : 'x-circle'"
							class="mx-auto h-12 w-12"
						/>
						<p class="mt-3 text-2xl-semibold">
							{{
								verification.data.is_valid
									? __("Active Membership")
									: __("Membership Not Active")
							}}
						</p>
					</div>

					<div class="divide-y divide-outline-gray-1">
						<div
							v-for="row in detailRows"
							:key="row.label"
							class="flex items-center justify-between gap-4 px-6 py-3"
						>
							<span class="text-sm-medium text-ink-gray-5">{{ row.label }}</span>
							<span class="text-right text-sm text-ink-gray-8">{{ row.value }}</span>
						</div>
						<div class="flex items-center justify-between gap-4 px-6 py-3">
							<span class="text-sm-medium text-ink-gray-5">{{ __("Status") }}</span>
							<Badge
								variant="outline"
								:theme="verification.data.is_valid ? 'green' : 'red'"
								size="lg"
							>
								{{ __(verification.data.status) }}
							</Badge>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Badge, Button, createResource, FeatherIcon } from "frappe-ui";
import { computed } from "vue";
import { useRoute } from "vue-router";
import vmmsLogo from "../assets/images/vmms.png";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import { sessionStore } from "../stores/session";

const route = useRoute();
const { branding } = sessionStore();

const brandLogo = computed(() => branding.data?.logo || vmmsLogo);
const brandName = computed(() => branding.data?.brand_name || "VMMS Portal");

const trustPoints = computed(() => [
	__("Digitally signed, tamper-proof QR codes"),
	__("Status checked live against our records"),
	__("No login required to verify"),
]);

const verification = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.verify_membership_qr",
	method: "GET",
	params: {
		membership: route.query.membership,
		token: route.query.token,
	},
	auto: true,
});

const detailRows = computed(() => {
	const d = verification.data;
	if (!d) return [];
	return [
		{ label: __("Member"), value: d.member_name },
		{ label: __("Membership"), value: d.membership },
		{ label: __("Membership Type"), value: d.membership_type },
		d.valid_from && { label: __("Valid From"), value: d.valid_from },
		d.valid_until && { label: __("Valid Until"), value: d.valid_until },
	].filter(Boolean);
});
</script>
