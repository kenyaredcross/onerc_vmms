<template>
  <span class="spinner" :class="`spinner--${size}`" :style="color ? { borderTopColor: color } : {}" role="status" aria-label="Loading" />
</template>

<script setup>
defineProps({
  size:  { type: String, default: 'md' },
  color: { type: String, default: null },
})
</script>

<style scoped>
.spinner {
  display: inline-block; border-radius: 50%;
  border: 2px solid rgba(0,0,0,0.12);
  border-top-color: var(--c-primary);
  animation: spin 0.65s linear infinite; flex-shrink: 0;
}
.spinner--xs { width: 12px; height: 12px; }
.spinner--sm { width: 16px; height: 16px; }
.spinner--md { width: 24px; height: 24px; border-width: 2.5px; }
.spinner--lg { width: 36px; height: 36px; border-width: 3px; }
.spinner--xl { width: 48px; height: 48px; border-width: 3px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
