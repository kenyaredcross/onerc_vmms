<template>
  <div class="p-3 border rounded-md bg-gray-50">
    <p class="text-xs font-semibold text-gray-500">{{ label }}</p>
    <ul v-if="items && items.length" class="list-disc ml-4 mt-1 text-gray-800">
      <li v-for="(item, i) in items" :key="i">{{ item }}</li>
    </ul>
    <p v-else class="mt-1 text-gray-400">—</p>
  </div>
</template>

<script setup>
defineProps({ label: String, items: Array });
</script>
