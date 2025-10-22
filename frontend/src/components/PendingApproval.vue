<template>
  <div class="h-screen bg-gray-50 flex items-center justify-center">
    <div class="max-w-6xl w-full grid grid-cols-1 md:grid-cols-2 gap-12 p-10">
      <div class="flex flex-col justify-center space-y-6 text-left">
        <h1
          class="text-3xl md:text-6xl font-extrabold text-red-600 leading-tight"
        >
          Application <br />
          <span class="text-gray-800">Received</span>
        </h1>
        <p class="text-lg text-gray-600 max-w-lg">
          Thank you for your interest in joining the
          <span class="font-semibold text-red-500">Kenya Red Cross Society</span
          >. Your application is now
          <span class="text-red-500 font-semibold">under review</span>
          and we'll get back to you soon.
        </p>
      </div>

      <div class="flex flex-col items-center justify-center space-y-6">
        <div
          class="bg-white rounded-2xl p-8 shadow-lg max-w-sm w-full text-center"
        >
          <div
            class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4"
          >
            <svg
              class="w-8 h-8 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              ></path>
            </svg>
          </div>
          <h3 class="text-xl font-bold text-gray-800 mb-2">
            We've Got Your Application!
          </h3>
          <p class="text-gray-600 mb-6">
            Our team is currently reviewing your submission.
          </p>
          <div class="space-y-3"></div>
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup></script>
