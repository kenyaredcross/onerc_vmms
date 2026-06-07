<template>
  <nav class="steps" :aria-label="`Step ${current + 1} of ${steps.length}`">
    <div
      v-for="(step, i) in steps" :key="i"
      class="step" :class="{ 'step--done': i < current, 'step--active': i === current }"
    >
      <div class="step__track" v-if="i > 0" :class="{ 'step__track--filled': i <= current }" />
      <div class="step__circle">
        <Check v-if="i < current" :size="14" />
        <span v-else>{{ i + 1 }}</span>
      </div>
      <span class="step__label">{{ step }}</span>
    </div>
  </nav>
</template>

<script setup>
import { Check } from 'lucide-vue-next'
defineProps({
  steps:   { type: Array, required: true },
  current: { type: Number, default: 0 },
})
</script>

<style scoped>
.steps {
  display: flex; align-items: flex-start; gap: 0;
  overflow-x: auto; padding: 2px 0 6px;
}
.step {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; gap: 6px; position: relative; min-width: 64px;
}
.step__track {
  position: absolute; top: 15px; right: calc(50% + 18px); left: calc(-50% + 18px);
  height: 2px; background: var(--c-border); transition: background var(--t-slow);
}
.step__track--filled { background: var(--c-primary); }
.step__circle {
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; z-index: 1;
  border: 2px solid var(--c-border); color: var(--c-text-muted);
  background: var(--c-surface); transition: all var(--t-base);
}
.step__label { font-size: 11px; font-weight: 500; color: var(--c-text-muted); text-align: center; line-height: 1.3; }

.step--done .step__circle { background: var(--c-primary); border-color: var(--c-primary); color: #fff; }
.step--done .step__label  { color: var(--c-primary); }
.step--active .step__circle { border-color: var(--c-primary); color: var(--c-primary); background: var(--c-primary-subtle); }
.step--active .step__label  { color: var(--c-primary); font-weight: 700; }
</style>
