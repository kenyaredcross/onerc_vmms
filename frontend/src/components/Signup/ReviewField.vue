<template>
  <div class="p-3 border rounded-md bg-gray-50">
    <p class="text-xs font-semibold text-gray-500">{{ label }}</p>
    <p class="mt-1 text-gray-800">
      {{ value ? value : "—" }}
    </p>
  </div>
</template>

<script setup>
defineProps({ label: String, value: [String, Number, Object] });
</script>
