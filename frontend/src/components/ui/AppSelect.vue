<template>
  <div class="field" :class="{ 'field--error': error, 'field--disabled': disabled }">
    <label v-if="label" :for="uid" class="field__label">
      {{ label }}<span v-if="required" class="field__req">*</span>
    </label>
    <div class="field__wrap">
      <select
        :id="uid"
        :value="modelValue"
        :disabled="disabled"
        :required="required"
        class="field__control"
        @change="$emit('update:modelValue', $event.target.value)"
      >
        <option v-if="placeholder" value="" :selected="!modelValue" disabled>{{ placeholder }}</option>
        <option v-for="opt in normalizedOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <ChevronDown :size="15" class="field__chevron" />
    </div>
    <p v-if="error" class="field__hint field__hint--error" role="alert">{{ error }}</p>
    <p v-else-if="hint" class="field__hint">{{ hint }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  label: String, placeholder: String, error: String, hint: String,
  required: Boolean, disabled: Boolean, id: String,
  valueKey: { type: String, default: 'value' },
  labelKey: { type: String, default: 'label' },
})
defineEmits(['update:modelValue'])
const uid = computed(() => props.id || `sel-${Math.random().toString(36).slice(2,8)}`)
const normalizedOptions = computed(() => props.options.map(o =>
  typeof o === 'string' ? { value: o, label: o } : { value: o[props.valueKey], label: o[props.labelKey] || o[props.valueKey] }
))
</script>

<style scoped>
.field { display: flex; flex-direction: column; gap: 5px; }
.field__label { font-size: 13px; font-weight: 600; color: var(--c-text); }
.field__req { color: var(--c-primary); margin-left: 2px; }
.field__wrap { position: relative; }
.field__control {
  width: 100%; padding: 9px 36px 9px 13px;
  border: 1.5px solid var(--c-border); border-radius: var(--radius-md);
  background: var(--c-surface); color: var(--c-text); font-size: 14px;
  appearance: none; outline: none; cursor: pointer;
  transition: border-color var(--t-base), box-shadow var(--t-base);
}
.field__control:focus { border-color: var(--c-primary); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-primary) 15%, transparent); }
.field__control:disabled { background: var(--c-border-subtle); color: var(--c-text-muted); cursor: not-allowed; }
.field--error .field__control { border-color: var(--c-error); }
.field__chevron { position: absolute; right: 11px; top: 50%; transform: translateY(-50%); color: var(--c-text-muted); pointer-events: none; }
.field__hint { font-size: 12px; color: var(--c-text-muted); }
.field__hint--error { color: var(--c-error); font-weight: 500; }
</style>
