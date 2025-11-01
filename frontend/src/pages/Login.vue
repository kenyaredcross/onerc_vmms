<template>
	<div class="flex min-h-screen items-center justify-center bg-gray-50">
		<Card
			:title="isLogin ? __('Login VMMS Portal') : __('Sign Up VMMS Portal')"
			:class="isLogin ? 'w-full max-w-md' : 'w-full max-w-2xl'"
			class="border-2 border-gray-100 shadow-md rounded-2xl"
		>
			<form class="flex flex-col space-y-4 w-full" @submit.prevent="submit">
				<template v-if="isLogin">
					<Input
						required
						name="email"
						type="text"
						:placeholder="__('johndoe@email.com')"
						:label="__('Email')"
						v-model="userEmail"
					/>

					<div class="flex items-center space-x-2">
						<Input
							class="w-full"
							required
							name="password"
							:type="passWordVisible ? 'text' : 'password'"
							:placeholder="__('••••••')"
							:label="__('Password')"
							v-model="password"
						/>

						<Eye
							v-if="!passWordVisible"
							class="w-5 h-5 mt-6 cursor-pointer text-gray-600"
							@click="passWordVisible = !passWordVisible"
						/>

						<EyeOff
							v-if="passWordVisible"
							class="w-5 h-5 mt-6 cursor-pointer text-gray-600"
							@click="passWordVisible = !passWordVisible"
						/>
					</div>
					<button type="button" @click="forgotPassword">
						<span class="text-sm text-right text-red-600 hover:underline">{{
							__("Forgot Password?")
						}}</span>
					</button>
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
				>
					{{ isLogin ? __("Login") : __("Sign Up") }}
				</Button>
			</form>

			<div class="mt-2 text-center">
				<ErrorMessage :message="isLogin ? session.login.error : createSignUp.error" />
			</div>

			<div class="mt-4 text-center text-sm">
				<span v-if="isLogin">{{ __("Don’t have an account?") }} </span>
				<span v-else>{{ __("Already have an account?") }} </span>
				<Button
					class="text-red-600 hover:underline font-medium"
					@click="toggleForm"
					type="button"
				>
					{{ isLogin ? __("Sign up") : __("Login") }}
				</Button>
			</div>
		</Card>
	</div>

	<Dialog
		:options="{
			title: __('Successfully Registered'),
			message: __(
				'We have sent you an email with a link to set your password. Please check your inbox (and spam folder) to complete your registration.',
			),
			size: 'lg',
			icon: {
				name: 'check-circle',
				appearance: 'success',
			},
		}"
		v-model="signInState"
	/>
</template>

<script setup lang="ts">
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
import { initialForm, resetSignUpForm, SignUp } from "../utils/volunteer";

const route = useRoute();
const router = useRouter();

const passWordVisible = ref(false);
const userEmail = ref("");
const password = ref("");
const signInState = ref(false);

const signUpForm = reactive<SignUp>({ ...initialForm });

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
	if (!route.hash) {
	}
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
					const redirectTo = route.query["redirect-to"] as string;
					if (redirectTo) {
						router.push(redirectTo);
					} else {
						router.push({ name: "Dashboard" });
					}
				},
			},
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
