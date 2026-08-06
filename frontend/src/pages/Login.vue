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
				<span class="text-2xl-semibold tracking-wide">{{ __(brandName) || "VMMS" }}</span>
			</div>

			<div class="relative max-w-md">
				<p class="text-sm-medium uppercase tracking-[0.2em] text-red-200">
					{{ __("Volunteer & Member Portal") }}
				</p>
				<h1 class="mt-3 text-5xl-bold leading-tight">
					{{ __("Serve. Belong.") }}<br />
					{{ __("Make a difference.") }}
				</h1>
				<p class="mt-4 text-red-100">
					{{
						__(
							"Manage your membership, discover volunteer opportunities, and stay connected with your community — all in one place."
						)
					}}
				</p>

				<ul class="mt-8 space-y-3 text-sm text-red-50">
					<li v-for="point in highlights" :key="point" class="flex items-center gap-3">
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
				&copy; {{ new Date().getFullYear() }} {{ __(brandName) }}
			</p>
		</div>

		<div
			class="flex w-full flex-col items-center justify-center bg-surface-gray-1 px-4 py-10 lg:w-1/2"
		>
			<div class="mb-8 flex items-center gap-3 lg:hidden">
				<img
					:src="brandLogo"
					:alt="brandName"
					class="h-10 w-10 rounded-lg object-contain"
				/>
				<span class="text-lg-semibold text-ink-gray-9">{{ __(brandName) }}</span>
			</div>

			<div
				:class="isLogin ? 'max-w-md' : 'max-w-2xl'"
				class="w-full rounded-2xl border border-outline-gray-1 bg-surface-base shadow-lg"
			>
				<div class="px-8 pt-8 pb-4 border-b border-outline-gray-1">
					<h1 class="text-3xl-semibold text-ink-gray-9">
						{{ isLogin ? __("Welcome back") : __("Create an account") }}
					</h1>
					<p class="mt-1 text-sm text-ink-gray-5">
						{{
							isLogin
								? __("Sign in to your VMMS Portal account")
								: __("Get started with the VMMS Portal")
						}}
					</p>
				</div>

				<form class="px-8 py-6 flex flex-col space-y-4" @submit.prevent="submit">
					<template v-if="isLogin">
						<Input
							required
							name="email"
							type="email"
							autocomplete="username"
							:placeholder="__('johndoe@email.com')"
							:label="__('Email')"
							v-model="userEmail"
						/>

						<div>
							<div class="flex items-end gap-2">
								<Input
									class="flex-1"
									required
									name="password"
									autocomplete="current-password"
									:type="passWordVisible ? 'text' : 'password'"
									:placeholder="__('••••••')"
									:label="__('Password')"
									v-model="password"
								/>
								<button
									type="button"
									class="mb-0.5 p-2 rounded-lg text-ink-gray-4 hover:text-ink-gray-6 hover:bg-surface-gray-2 transition-colors"
									:aria-label="
										passWordVisible ? __('Hide password') : __('Show password')
									"
									:aria-pressed="passWordVisible"
									@click="passWordVisible = !passWordVisible"
								>
									<Eye v-if="!passWordVisible" class="w-4 h-4" />
									<EyeOff v-else class="w-4 h-4" />
								</button>
							</div>
							<div class="mt-1 text-right">
								<button
									type="button"
									class="text-xs text-ink-red-6 hover:underline"
									@click="forgotPassword"
								>
									{{ __("Forgot Password?") }}
								</button>
							</div>
						</div>
					</template>

					<template v-else>
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
							<Input
								required
								name="firstname"
								type="text"
								autocomplete="given-name"
								:placeholder="__('John')"
								:label="__('First Name')"
								v-model="signUpForm.first_name"
							/>
							<Input
								required
								name="lastname"
								type="text"
								autocomplete="family-name"
								:placeholder="__('Doe')"
								:label="__('Last Name')"
								v-model="signUpForm.last_name"
							/>
						</div>
						<Input
							required
							name="email"
							type="email"
							autocomplete="email"
							:placeholder="__('johndoe@email.com')"
							:label="__('Email')"
							v-model="signUpForm.email"
						/>
					</template>

					<Button
						:loading="isLogin ? session.login.loading : createSignUp.loading"
						variant="solid"
						type="submit"
						theme="red"
						class="w-full"
					>
						{{ isLogin ? __("Login") : __("Sign Up") }}
					</Button>

					<ErrorMessage
						class="text-center"
						:message="isLogin ? session.login.error : createSignUp.error"
					/>
				</form>

				<div
					class="px-8 py-4 border-t border-outline-gray-1 text-center text-sm text-ink-gray-5"
				>
					<span>{{
						isLogin ? __("Don't have an account?") : __("Already have an account?")
					}}</span>
					<button
						type="button"
						class="ml-1 font-medium text-ink-red-6 hover:underline"
						@click="toggleForm"
					>
						{{ isLogin ? __("Sign up") : __("Login") }}
					</button>
				</div>
			</div>
		</div>
	</div>

	<Dialog
		:options="{
			title: __('Successfully Registered'),
			message: __(
				'We have sent you an email with a link to set your password. Please check your inbox (and spam folder) to complete your registration.'
			),
			size: 'lg',
			icon: { name: 'check-circle', appearance: 'success' },
		}"
		v-model="signInState"
	/>
</template>

<script setup>
import { Button, createResource, Dialog, ErrorMessage, FeatherIcon, Input } from "frappe-ui";
import { Eye, EyeOff } from "lucide-vue-next";
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import vmmsLogo from "../assets/images/vmms.png";
import { sessionStore } from "../stores/session";
import { initialForm, resetSignUpForm } from "../utils/volunteer";

const route = useRoute();
const router = useRouter();

const { branding } = sessionStore();
const brandLogo = computed(() => branding.data?.logo || vmmsLogo);
const brandName = computed(() => branding.data?.brand_name || "VMMS Portal");
const highlights = computed(() => [
	__("Become a member or renew in minutes"),
	__("Find and apply for volunteer opportunities"),
	__("Track your events, deployments and applications"),
]);

const passWordVisible = ref(false);
const userEmail = ref("");
const password = ref("");
const signInState = ref(false);

const signUpForm = reactive({ ...initialForm });

const session = sessionStore();
let { isLoggedIn } = sessionStore();

const isLogin = computed(() => route.hash !== "#signup");

function toggleForm() {
	if (isLogin.value) {
		router.replace({ hash: "#signup" });
	} else {
		router.replace({ hash: "#login" });
	}
}

onMounted(() => {
	if (isLoggedIn) {
		router.push({ name: "Dashboard" });
	}
});

const createSignUp = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.create_user",
	onSuccess() {
		signInState.value = true;
		resetSignUpForm(signUpForm);
		router.replace({ hash: "#login" });
	},
});

function submit() {
	if (isLogin.value) {
		session.login.submit(
			{ usr: userEmail.value, pwd: password.value },
			{
				onSuccess: () => {
					const redirectTo = route.query["redirect-to"];
					if (redirectTo) {
						router.push(redirectTo);
					} else {
						router.push({ name: "Dashboard" });
					}
				},
			}
		);
	} else {
		createSignUp.submit({
			...signUpForm,
		});
	}
}

function forgotPassword() {
	window.location.href = "/login#forgot";
}
</script>
