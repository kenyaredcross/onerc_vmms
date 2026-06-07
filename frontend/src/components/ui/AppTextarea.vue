<template>
  <div class="field" :class="{ 'field--error': error }">
    <label v-if="label" :for="uid" class="field__label">
      {{ label }}<span v-if="required" class="field__req">*</span>
    </label>
    <textarea
      :id="uid" :value="modelValue" :placeholder="placeholder"
      :rows="rows" :disabled="disabled" :required="required"
      class="field__control"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <p v-if="error" class="field__hint field__hint--error" role="alert">{{ error }}</p>
    <p v-else-if="hint" class="field__hint">{{ hint }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  modelValue: { type: String, default: '' },
  label: String, placeholder: String, error: String, hint: String,
  required: Boolean, disabled: Boolean, rows: { type: Number, default: 3 }, id: String,
})
defineEmits(['update:modelValue'])
const uid = computed(() => props.id || `ta-${Math.random().toString(36).slice(2,8)}`)
</script>

<style scoped>
.field { display: flex; flex-direction: column; gap: 5px; }
.field__label { font-size: 13px; font-weight: 600; color: var(--c-text); }
.field__req { color: var(--c-primary); margin-left: 2px; }
.field__control {
  width: 100%; padding: 9px 13px; resize: vertical;
  border: 1.5px solid var(--c-border); border-radius: var(--radius-md);
  background: var(--c-surface); color: var(--c-text); font-size: 14px;
  line-height: 1.5; outline: none; min-height: 80px;
  transition: border-color var(--t-base), box-shadow var(--t-base);
}
.field__control::placeholder { color: var(--c-text-muted); }
.field__control:focus { border-color: var(--c-primary); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-primary) 15%, transparent); }
.field--error .field__control { border-color: var(--c-error); }
.field__hint { font-size: 12px; color: var(--c-text-muted); }
.field__hint--error { color: var(--c-error); font-weight: 500; }
</style>
