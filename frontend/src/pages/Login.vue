<template>
	<div class="flex min-h-screen items-center justify-center bg-surface-gray-1">
		<div
			:class="isLogin ? 'max-w-md' : 'max-w-2xl'"
			class="w-full rounded-2xl border border-outline-gray-1 bg-surface-white shadow-lg"
		>
			<!-- Header -->
			<div class="px-8 pt-8 pb-4 border-b border-outline-gray-1">
				<h1 class="text-2xl font-semibold text-ink-gray-9">
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

			<!-- Form -->
			<form class="px-8 py-6 flex flex-col space-y-4" @submit.prevent="submit">
				<template v-if="isLogin">
					<Input
						required
						name="email"
						type="text"
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
								:type="passWordVisible ? 'text' : 'password'"
								:placeholder="__('••••••')"
								:label="__('Password')"
								v-model="password"
							/>
							<button
								type="button"
								class="mb-0.5 p-2 rounded-lg text-ink-gray-4 hover:text-ink-gray-6 hover:bg-surface-gray-2 transition-colors"
								@click="passWordVisible = !passWordVisible"
							>
								<Eye v-if="!passWordVisible" class="w-4 h-4" />
								<EyeOff v-else class="w-4 h-4" />
							</button>
						</div>
						<div class="mt-1 text-right">
							<button
								type="button"
								class="text-xs text-ink-red-3 hover:underline"
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
							:placeholder="__('John')"
							:label="__('First Name')"
							v-model="signUpForm.first_name"
						/>
						<Input
							required
							name="lastname"
							type="text"
							:placeholder="__('Doe')"
							:label="__('Last Name')"
							v-model="signUpForm.last_name"
						/>
					</div>
					<Input
						required
						name="email"
						type="text"
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

			<!-- Footer -->
			<div
				class="px-8 py-4 border-t border-outline-gray-1 text-center text-sm text-ink-gray-5"
			>
				<span>{{
					isLogin ? __("Don't have an account?") : __("Already have an account?")
				}}</span>
				<button
					type="button"
					class="ml-1 font-medium text-ink-red-3 hover:underline"
					@click="toggleForm"
				>
					{{ isLogin ? __("Sign up") : __("Login") }}
				</button>
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
import { createResource } from "frappe-ui";
import Button from "frappe-ui/src/components/Button/Button.vue";
import Card from "frappe-ui/src/components/Card.vue";
import Dialog from "frappe-ui/src/components/Dialog/Dialog.vue";
import ErrorMessage from "frappe-ui/src/components/ErrorMessage/ErrorMessage.vue";
import Input from "frappe-ui/src/components/Input.vue";
import { Eye, EyeOff } from "lucide-vue-next";
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { sessionStore } from "../stores/session";
import { initialForm, resetSignUpForm } from "../utils/volunteer";

const route = useRoute();
const router = useRouter();

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
