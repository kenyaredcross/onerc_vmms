<template>
  <div class="card" :class="[`card--${padding}`, { 'card--hover': hover, 'card--flat': flat }]">
    <div v-if="$slots.header" class="card__header"><slot name="header" /></div>
    <div class="card__body"><slot /></div>
    <div v-if="$slots.footer" class="card__footer"><slot name="footer" /></div>
  </div>
</template>

<script setup>
defineProps({
  padding: { type: String, default: 'md' },
  hover:   { type: Boolean, default: false },
  flat:    { type: Boolean, default: false },
})
</script>

<style scoped>
.card {
  background: var(--c-surface); border-radius: var(--radius-lg);
  border: 1px solid var(--c-border); box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.card--hover { transition: box-shadow var(--t-base), transform var(--t-base); cursor: pointer; }
.card--hover:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.card--flat { box-shadow: none; }

.card__header {
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--c-border);
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-3);
}
.card__footer {
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--c-border);
  background: var(--c-border-subtle);
  display: flex; align-items: center; justify-content: flex-end;
  gap: var(--space-2);
}

.card--none .card__body { padding: 0; }
.card--sm  .card__body { padding: var(--space-3); }
.card--md  .card__body { padding: var(--space-5); }
.card--lg  .card__body { padding: var(--space-8); }
</style>
