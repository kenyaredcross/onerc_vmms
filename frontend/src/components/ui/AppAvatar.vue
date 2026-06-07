<template>
  <div class="avatar" :class="`avatar--${size}`" :style="{ background: bgColor }">
    <img v-if="photo" :src="photo" :alt="name" class="avatar__img" />
    <span v-else class="avatar__initials">{{ initials }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  name:  { type: String, default: '' },
  photo: { type: String, default: null },
  size:  { type: String, default: 'md' },
})
const initials = computed(() => {
  return (props.name || '?').split(' ').filter(Boolean).map(w => w[0]).slice(0,2).join('').toUpperCase()
})
const bgColor = computed(() => {
  const colors = ['#EE2435','#011E41','#059669','#D97706','#7C3AED','#0369A1','#DC2626']
  let h = 0
  for (let i = 0; i < (props.name || '').length; i++) h = props.name.charCodeAt(i) + ((h << 5) - h)
  return colors[Math.abs(h) % colors.length]
})
</script>

<style scoped>
.avatar {
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; font-weight: 700; color: #fff; overflow: hidden;
}
.avatar--xs { width: 24px; height: 24px; font-size: 10px; }
.avatar--sm { width: 32px; height: 32px; font-size: 12px; }
.avatar--md { width: 40px; height: 40px; font-size: 14px; }
.avatar--lg { width: 56px; height: 56px; font-size: 18px; }
.avatar--xl { width: 80px; height: 80px; font-size: 26px; }
.avatar--2xl{ width: 112px; height: 112px; font-size: 36px; }
.avatar__img { width: 100%; height: 100%; object-fit: cover; }
.avatar__initials { line-height: 1; letter-spacing: 0.02em; }
</style>
