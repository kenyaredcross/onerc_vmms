<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-50">
    <Card
      :title="isLogin ? 'Login VMMS Portal' : 'Sign Up VMMS Portal'"
      :class="isLogin ? 'w-full max-w-md' : 'w-full max-w-2xl'"
      class="border-2 border-gray-100 shadow-md rounded-2xl"
    >
      <form class="flex flex-col space-y-4 w-full" @submit.prevent="submit">
        <template v-if="isLogin">
          <Input
            required
            name="email"
            type="text"
            placeholder="johndoe@email.com"
            label="Email"
            v-model="userEmail"
          />

          <div class="flex items-center space-x-2">
            <Input
              class="w-full"
              required
              name="password"
              :type="passWordVisible ? 'text' : 'password'"
              placeholder="••••••"
              label="Password"
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
            <span class="text-sm text-right text-red-600 hover:underline"
              >Forgot Password?</span
            >
          </button>
        </template>

        <template v-else>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              required
              name="firstname"
              type="text"
              placeholder="John"
              label="First Name"
              v-model="signUpForm.first_name"
            />
            <Input
              required
              name="lastname"
              type="text"
              placeholder="Doe"
              label="Last Name"
              v-model="signUpForm.last_name"
            />
          </div>

          <Input
            required
            name="email"
            type="text"
            placeholder="johndoe@email.com"
            label="Email"
            v-model="signUpForm.email"
          />

          <Input
            required
            type="text"
            variant="subtle"
            placeholder="+254123456789"
            label="Phone Number"
            v-model="signUpForm.phone"
          />

          <div>
            <label class="text-gray-700 text-sm mb-2 block">Gender</label>
            <Select
              required
              v-model="signUpForm.gender"
              :options="genderOptions"
              placeholder="Select Gender"
              class="focus:ring-2 focus:ring-red-500"
            />
          </div>
        </template>

        <Button
          :loading="isLogin ? session.login.loading : createSignUp.loading"
          variant="solid"
          type="submit"
          theme="red"
        >
          {{ isLogin ? "Login" : "Sign Up" }}
        </Button>
      </form>

      <div class="mt-2 text-center">
        <ErrorMessage
          :message="isLogin ? session.login.error : createSignUp.error"
        />
      </div>

      <div class="mt-4 text-center text-sm">
        <span v-if="isLogin">Don’t have an account? </span>
        <span v-else>Already have an account? </span>
        <Button
          class="text-red-600 hover:underline font-medium"
          @click="toggleForm"
          type="button"
        >
          {{ isLogin ? "Sign up" : "Login" }}
        </Button>
      </div>
    </Card>
  </div>

  <Dialog
    :options="{
      title: 'Successfully Registered',
      message:
        'We have sent you an email with a link to set your password. Please check your inbox (and spam folder) to complete your registration.',
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
import Button from "frappe-ui/src/components/Button/Button.vue";
import { sessionStore } from "../stores/session";
import Card from "frappe-ui/src/components/Card.vue";
import Input from "frappe-ui/src/components/Input.vue";
import { computed, onMounted, reactive, ref } from "vue";
import ErrorMessage from "frappe-ui/src/components/ErrorMessage/ErrorMessage.vue";
import { createResource, Select } from "frappe-ui";
import Dialog from "frappe-ui/src/components/Dialog/Dialog.vue";
import {
  SignUp,
  initialForm,
  isValidPhone,
  resetSignUpForm,
} from "../utils/volunteer";
import { useRoute, useRouter } from "vue-router";
import { Eye, EyeOff } from "lucide-vue-next";

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

const genderOptions = [
  { label: "Male", value: "Male" },
  { label: "Female", value: "Female" },
  { label: "Other", value: "Other" },
];

const createSignUp = createResource({
  url: "non_profit.non_profit.user.create_user",
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
      }
    );
  } else {
    if (!isValidPhone(signUpForm.phone)) {
      createSignUp.error =
        "Please enter a valid Kenyan phone number.eg. (+254123456789)";
      return;
    }
    createSignUp.submit({
      ...signUpForm,
    });
  }
}

function forgotPassword() {
  window.location.href = "/login#forgot";
}
</script>
