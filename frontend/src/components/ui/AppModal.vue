<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="modal-backdrop" @click.self="closeOnBackdrop && close()">
        <div class="modal" :class="`modal--${size}`" role="dialog" :aria-modal="true" :aria-label="title">
          <div class="modal__header">
            <h3 class="modal__title">{{ title }}</h3>
            <button class="modal__close" @click="close" aria-label="Close modal"><X :size="18" /></button>
          </div>
          <div class="modal__body"><slot /></div>
          <div v-if="$slots.footer" class="modal__footer"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { X } from 'lucide-vue-next'
const props = defineProps({
  modelValue:       { type: Boolean, default: false },
  title:            { type: String, default: '' },
  size:             { type: String, default: 'md' },
  closeOnBackdrop:  { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue'])
function close() { emit('update:modelValue', false) }
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.45); backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center; padding: 16px;
}
.modal {
  background: var(--c-surface); border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg); width: 100%; max-height: 92vh;
  display: flex; flex-direction: column; overflow: hidden;
}
.modal--sm  { max-width: 420px; }
.modal--md  { max-width: 560px; }
.modal--lg  { max-width: 720px; }
.modal--xl  { max-width: 960px; }
.modal__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 22px 16px; border-bottom: 1px solid var(--c-border); flex-shrink: 0;
}
.modal__title { font-size: 17px; font-weight: 700; color: var(--c-text); }
.modal__close {
  background: none; border: none; color: var(--c-text-muted); cursor: pointer;
  padding: 4px; border-radius: var(--radius-sm); transition: all var(--t-fast);
}
.modal__close:hover { background: var(--c-border-subtle); color: var(--c-text); }
.modal__body { padding: 20px 22px; overflow-y: auto; flex: 1; }
.modal__footer {
  padding: 14px 22px; border-top: 1px solid var(--c-border);
  display: flex; justify-content: flex-end; gap: 8px; flex-shrink: 0;
  background: var(--c-border-subtle);
}

.modal-enter-active, .modal-leave-active { transition: all 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal { transform: scale(0.95) translateY(8px); }
</style>
