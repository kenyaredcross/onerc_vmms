<template>
  <div class="geo">
    <p class="geo__hint">Select your location from the highest level down.</p>
    <div v-for="(level, idx) in levels" :key="level.geo_level_key" class="geo__level">
      <AppSelect
        :label="level.geo_level_name"
        :placeholder="`Select ${level.geo_level_name}…`"
        :options="options[idx] || []"
        :model-value="selections[idx]"
        :disabled="idx > 0 && !selections[idx - 1]"
        value-key="name"
        label-key="geo_node_name"
        @update:model-value="v => onSelect(idx, v)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import http from '../../lib/axios'
import AppSelect from './AppSelect.vue'

const props = defineProps({
  levels:     { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const selections = ref([])
const options    = ref([])

watch(() => props.levels, lvls => {
  selections.value = lvls.map(() => '')
  options.value    = lvls.map(() => [])
  if (lvls.length > 0) load(0, null)
}, { immediate: true })

async function load(idx, parent) {
  if (idx >= props.levels.length) return
  try {
    const params = { geo_level: props.levels[idx].name }
    if (parent) params.parent_geo_node = parent
    const { data } = await http.get('/api/method/onerc_core.api.geo.get_geo_nodes', { params })
    options.value[idx] = data.message || []
  } catch { options.value[idx] = [] }
}

function onSelect(idx, val) {
  selections.value[idx] = val
  for (let i = idx + 1; i < props.levels.length; i++) {
    selections.value[i] = ''
    options.value[i] = []
  }
  if (val && idx + 1 < props.levels.length) load(idx + 1, val)
  emit('update:modelValue', [...selections.value].reverse().find(v => v) || '')
}
</script>

<style scoped>
.geo { display: flex; flex-direction: column; gap: 14px; }
.geo__hint { font-size: 13px; color: var(--c-text-muted); margin-bottom: 2px; }
</style>
