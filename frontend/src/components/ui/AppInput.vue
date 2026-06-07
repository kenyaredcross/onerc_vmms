<template>
  <div class="field" :class="{ 'field--error': error, 'field--disabled': disabled }">
    <label v-if="label" :for="uid" class="field__label">
      {{ label }}<span v-if="required" class="field__req" aria-hidden="true">*</span>
    </label>
    <div class="field__wrap">
      <component :is="prefixIcon" v-if="prefixIcon" :size="16" class="field__icon field__icon--left" />
      <input
        :id="uid"
        :value="modelValue"
        :type="type"
        :placeholder="placeholder"
        :disabled="disabled"
        :required="required"
        :min="min" :max="max"
        :autocomplete="autocomplete"
        class="field__control"
        :class="{ 'has-prefix': prefixIcon }"
        @input="$emit('update:modelValue', $event.target.value)"
        @blur="$emit('blur', $event)"
      />
    </div>
    <p v-if="error" class="field__hint field__hint--error" role="alert">{{ error }}</p>
    <p v-else-if="hint" class="field__hint">{{ hint }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  modelValue:  { type: [String, Number], default: '' },
  label:       String,
  type:        { type: String, default: 'text' },
  placeholder: String,
  error:       String,
  hint:        String,
  required:    Boolean,
  disabled:    Boolean,
  prefixIcon:  { type: [Object, Function], default: null },
  min: String, max: String,
  autocomplete: String,
  id: String,
})
defineEmits(['update:modelValue', 'blur'])
const uid = computed(() => props.id || `input-${Math.random().toString(36).slice(2,8)}`)
</script>

<style scoped>
.field { display: flex; flex-direction: column; gap: 5px; }
.field__label { font-size: 13px; font-weight: 600; color: var(--c-text); }
.field__req { color: var(--c-primary); margin-left: 2px; }
.field__wrap { position: relative; }
.field__icon { position: absolute; top: 50%; transform: translateY(-50%); color: var(--c-text-muted); pointer-events: none; }
.field__icon--left { left: 12px; }
.field__control {
  width: 100%; padding: 9px 13px;
  border: 1.5px solid var(--c-border); border-radius: var(--radius-md);
  background: var(--c-surface); color: var(--c-text); font-size: 14px;
  transition: border-color var(--t-base), box-shadow var(--t-base); outline: none;
}
.field__control.has-prefix { padding-left: 38px; }
.field__control::placeholder { color: var(--c-text-muted); }
.field__control:focus { border-color: var(--c-primary); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-primary) 15%, transparent); }
.field__control:disabled { background: var(--c-border-subtle); color: var(--c-text-muted); cursor: not-allowed; }
.field--error .field__control { border-color: var(--c-error); }
.field--error .field__control:focus { box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-error) 15%, transparent); }
.field__hint { font-size: 12px; color: var(--c-text-muted); }
.field__hint--error { color: var(--c-error); font-weight: 500; }
</style>
