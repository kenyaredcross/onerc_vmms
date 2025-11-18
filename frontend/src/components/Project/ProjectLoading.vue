<template>
    <div class="flex items-center justify-center min-h-screen">
        <div class="flex flex-col justify-center items-center text-center text-red-800">
            <Spinner class="w-12" />
            <p class="text-gray-600">{{ __("Loading project details...") }}</p>
        </div>
    </div>
</template>

<script setup>
import { Spinner } from "frappe-ui";
</script>