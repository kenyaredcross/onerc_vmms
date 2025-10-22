<template>
  <div
    class="flex flex-col items-center justify-center py-20 h-[75vh] bg-gray-50 m-8 md:m-16 text-center px-4"
  >
    <div class="bg-red-100 rounded-full p-6 mb-6 shadow-md">
      <LogIn class="w-12 h-12 text-red-600" />
    </div>

    <h2 class="text-3xl md:text-4xl font-extrabold text-gray-900 mb-4">
      🔒 Authentication Required
    </h2>

    <p class="text-gray-600 mb-8 max-w-md">
      Please log in to access your {{ page }} and continue exploring our
      features.
    </p>

    <div
      variant="solid"
      class="bg-red-600 hover:bg-red-700 text-white px-8 py-3 flex items-center gap-3 rounded-xl shadow-lg cursor-pointer"
      @click="redirectToLogin"
    >
      <LogIn class="w-5 h-5" />
      Login
    </div>
  </div>
</template>
<script setup>
import { LogIn } from "lucide-vue-next";
import router from "../router";
function redirectToLogin() {
  router.push("/login");
}

defineProps({
  page: String,
});
</script>
